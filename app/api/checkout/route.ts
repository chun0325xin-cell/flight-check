import { env } from "cloudflare:workers";

const packages: Record<string, { name: string; deposit: number }> = {
  "portrait-30": { name: "Portrait Mini deposit", deposit: 1500 },
  "portrait-60": { name: "Portrait Classic deposit", deposit: 1800 },
  "portrait-90": { name: "Portrait Story deposit", deposit: 2600 },
  "group-60": { name: "Group Classic deposit", deposit: 2100 },
  "group-90": { name: "Group Story deposit", deposit: 2900 },
  "group-120": { name: "Group Full deposit", deposit: 3500 },
};

export async function POST(request: Request) {
  const { bookingId, packageId } = await request.json() as { bookingId?: string; packageId?: string };
  const item = packageId ? packages[packageId] : undefined;
  const secret = (env as unknown as { STRIPE_SECRET_KEY?: string }).STRIPE_SECRET_KEY;
  if (!secret || !item || !bookingId) return Response.json({ setupRequired: true });
  const origin = new URL(request.url).origin;
  const form = new URLSearchParams();
  form.set("mode", "payment");
  form.set("success_url", `${origin}/?payment=success&booking=${bookingId}`);
  form.set("cancel_url", `${origin}/?payment=cancelled#booking`);
  form.set("client_reference_id", bookingId);
  form.set("line_items[0][price_data][currency]", "usd");
  form.set("line_items[0][price_data][product_data][name]", item.name);
  form.set("line_items[0][price_data][unit_amount]", String(item.deposit));
  form.set("line_items[0][quantity]", "1");
  const response = await fetch("https://api.stripe.com/v1/checkout/sessions", {
    method: "POST",
    headers: { Authorization: `Bearer ${secret}`, "Content-Type": "application/x-www-form-urlencoded" },
    body: form,
  });
  if (!response.ok) return Response.json({ error: "Payment checkout could not start." }, { status: 502 });
  const session = await response.json() as { url?: string };
  return Response.json({ url: session.url });
}
