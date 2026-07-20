import { env } from "cloudflare:workers";

type BookingRequest = {
  packageId: string; packageName: string; date: string; time: string;
  name: string; email: string; phone: string; notes?: string; total: number; deposit: number;
};

type NotificationEnv = {
  RESEND_API_KEY?: string;
  BOOKING_EMAIL?: string;
  BOOKING_FROM_EMAIL?: string;
};

async function sendBookingNotification(id: string, body: BookingRequest) {
  const notificationEnv = env as unknown as NotificationEnv;
  if (!notificationEnv.RESEND_API_KEY || !notificationEnv.BOOKING_EMAIL) {
    return { sent: false, error: "Email settings are incomplete." };
  }

  const text = [
    "A new photoshoot was scheduled.",
    "",
    `Client: ${body.name}`,
    `Email: ${body.email}`,
    `Phone: ${body.phone}`,
    `Session: ${body.packageName}`,
    `Date: ${body.date}`,
    `Time: ${body.time}`,
    `Total: $${body.total}`,
    `Deposit: $${body.deposit}`,
    `Notes: ${body.notes || "None"}`,
    "",
    `Booking reference: ${id}`,
    "Payment status: awaiting Stripe checkout",
  ].join("\n");

  const response = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${notificationEnv.RESEND_API_KEY}`,
      "Content-Type": "application/json",
      "Idempotency-Key": `booking-${id}`,
    },
    body: JSON.stringify({
      from: notificationEnv.BOOKING_FROM_EMAIL || "Joli's Photo <onboarding@resend.dev>",
      to: [notificationEnv.BOOKING_EMAIL],
      reply_to: body.email,
      subject: `New booking: ${body.packageName} on ${body.date}`,
      text,
    }),
  });

  if (response.ok) return { sent: true };
  const providerMessage = (await response.text()).slice(0, 300);
  return { sent: false, error: `Resend ${response.status}: ${providerMessage}` };
}

const schema = `CREATE TABLE IF NOT EXISTS bookings (
  id TEXT PRIMARY KEY,
  package_id TEXT NOT NULL,
  package_name TEXT NOT NULL,
  session_date TEXT NOT NULL,
  session_time TEXT NOT NULL,
  customer_name TEXT NOT NULL,
  email TEXT NOT NULL,
  phone TEXT NOT NULL,
  notes TEXT,
  total_cents INTEGER NOT NULL,
  deposit_cents INTEGER NOT NULL,
  payment_status TEXT NOT NULL DEFAULT 'pending',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)`;

export async function POST(request: Request) {
  try {
    const body = await request.json() as BookingRequest;
    if (!body.packageId || !body.date || !body.time || !body.name || !body.email || !body.phone) {
      return Response.json({ error: "Please complete all required fields." }, { status: 400 });
    }
    const db = env.DB;
    if (!db) return Response.json({ id: crypto.randomUUID(), preview: true, notificationSent: false });
    await db.prepare(schema).run();
    await db.prepare("CREATE UNIQUE INDEX IF NOT EXISTS booking_time_idx ON bookings(session_date, session_time)").run();
    const id = crypto.randomUUID();
    await db.prepare(`INSERT INTO bookings
      (id, package_id, package_name, session_date, session_time, customer_name, email, phone, notes, total_cents, deposit_cents)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`)
      .bind(id, body.packageId, body.packageName, body.date, body.time, body.name, body.email, body.phone, body.notes || "", Math.round(body.total * 100), Math.round(body.deposit * 100)).run();
    let notificationResult: { sent: boolean; error?: string } = { sent: false };
    try {
      notificationResult = await sendBookingNotification(id, body);
    } catch (error) {
      // A temporary email-provider issue must never lose a valid reservation.
      notificationResult = { sent: false, error: error instanceof Error ? error.message : "Email request failed." };
    }
    return Response.json({
      id,
      notificationSent: notificationResult.sent,
      ...(body.packageId === "email-test" ? { notificationError: notificationResult.error } : {}),
    });
  } catch (error) {
    const text = error instanceof Error ? error.message : "Booking failed";
    if (text.includes("UNIQUE")) return Response.json({ error: "That time was just booked. Please choose another time." }, { status: 409 });
    return Response.json({ error: "We couldn’t reserve that time. Please try again." }, { status: 500 });
  }
}
