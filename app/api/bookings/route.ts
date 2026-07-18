import { env } from "cloudflare:workers";

type BookingRequest = {
  packageId: string; packageName: string; date: string; time: string;
  name: string; email: string; phone: string; notes?: string; total: number; deposit: number;
};

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
    if (!db) return Response.json({ id: crypto.randomUUID(), preview: true });
    await db.prepare(schema).run();
    await db.prepare("CREATE UNIQUE INDEX IF NOT EXISTS booking_time_idx ON bookings(session_date, session_time)").run();
    const id = crypto.randomUUID();
    await db.prepare(`INSERT INTO bookings
      (id, package_id, package_name, session_date, session_time, customer_name, email, phone, notes, total_cents, deposit_cents)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`)
      .bind(id, body.packageId, body.packageName, body.date, body.time, body.name, body.email, body.phone, body.notes || "", Math.round(body.total * 100), Math.round(body.deposit * 100)).run();
    return Response.json({ id });
  } catch (error) {
    const text = error instanceof Error ? error.message : "Booking failed";
    if (text.includes("UNIQUE")) return Response.json({ error: "That time was just booked. Please choose another time." }, { status: 409 });
    return Response.json({ error: "We couldn’t reserve that time. Please try again." }, { status: 500 });
  }
}
