"use client";

import { FormEvent, useMemo, useState } from "react";

type Package = {
  id: string;
  category: "Portraits" | "Group Photos";
  name: string;
  duration: string;
  photos: number;
  price: number;
};

const packages: Package[] = [
  { id: "portrait-30", category: "Portraits", name: "Portrait Mini", duration: "30 minutes", photos: 8, price: 35 },
  { id: "portrait-60", category: "Portraits", name: "Portrait Classic", duration: "1 hour", photos: 15, price: 60 },
  { id: "portrait-90", category: "Portraits", name: "Portrait Story", duration: "1.5 hours", photos: 22, price: 85 },
  { id: "group-60", category: "Group Photos", name: "Group Classic", duration: "1 hour", photos: 15, price: 70 },
  { id: "group-90", category: "Group Photos", name: "Group Story", duration: "1.5 hours", photos: 22, price: 95 },
  { id: "group-120", category: "Group Photos", name: "Group Full", duration: "2 hours", photos: 30, price: 115 },
];

const times = ["9:00 AM", "10:30 AM", "12:00 PM", "1:30 PM", "3:00 PM", "4:30 PM", "6:00 PM"];

function dateValue(offset: number) {
  const date = new Date();
  date.setDate(date.getDate() + offset);
  return date.toISOString().slice(0, 10);
}

function prettyDate(value: string) {
  if (!value) return "Choose a date";
  return new Intl.DateTimeFormat("en-US", { weekday: "short", month: "short", day: "numeric", timeZone: "UTC" }).format(new Date(`${value}T12:00:00Z`));
}

export default function Home() {
  const [selectedId, setSelectedId] = useState("portrait-60");
  const [date, setDate] = useState("");
  const [time, setTime] = useState("");
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [status, setStatus] = useState<"idle" | "saving" | "payment" | "success" | "error">("idle");
  const [message, setMessage] = useState("");
  const selected = useMemo(() => packages.find((item) => item.id === selectedId) ?? packages[1], [selectedId]);
  const deposit = Math.max(15, Math.round(selected.price * 0.3));

  function choosePackage(id: string) {
    setSelectedId(id);
    setStep(2);
    window.setTimeout(() => document.getElementById("booking")?.scrollIntoView({ behavior: "smooth" }), 50);
  }

  function continueToDetails() {
    if (!date || !time) {
      setMessage("Please choose both a date and time.");
      return;
    }
    setMessage("");
    setStep(3);
  }

  async function submitBooking(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus("saving");
    setMessage("");
    const form = new FormData(event.currentTarget);
    const payload = {
      packageId: selected.id,
      packageName: selected.name,
      date,
      time,
      name: form.get("name"),
      email: form.get("email"),
      phone: form.get("phone"),
      notes: form.get("notes"),
      total: selected.price,
      deposit,
    };

    try {
      const bookingResponse = await fetch("/api/bookings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!bookingResponse.ok) {
        const result = await bookingResponse.json() as { error?: string };
        throw new Error(result.error || "We couldn’t reserve that time.");
      }
      const booking = await bookingResponse.json() as { id: string };
      setStatus("payment");
      const paymentResponse = await fetch("/api/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ bookingId: booking.id, packageId: selected.id }),
      });
      const payment = await paymentResponse.json() as { url?: string; setupRequired?: boolean };
      if (payment.url) {
        window.location.href = payment.url;
        return;
      }
      setStatus("success");
      setMessage(payment.setupRequired
        ? "Your time is reserved! Joli will contact you to finish the deposit. Online card payment will appear here once the payment account is connected."
        : "Your time is reserved! Check your email for the next step.");
    } catch (error) {
      setStatus("error");
      setMessage(error instanceof Error ? error.message : "Something went wrong. Please try again.");
    }
  }

  return (
    <main>
      <nav className="nav">
        <a className="brand" href="#top" aria-label="Joli's Photos home">
          <span className="brand-mark">J</span>
          <span>Joli’s <i>Photos</i></span>
        </a>
        <div className="nav-links">
          <a href="#packages">Packages</a>
          <a href="#booking">Book</a>
          <a href="https://www.instagram.com/jolis.photos/" target="_blank" rel="noreferrer">Instagram</a>
        </div>
        <a className="button button-small" href="#booking">Book a shoot</a>
      </nav>

      <section className="hero" id="top">
        <div className="hero-copy">
          <p className="eyebrow">Portrait & group photography</p>
          <h1>Keep the moments<br />that feel like <em>you.</em></h1>
          <p className="hero-text">Warm, relaxed photo sessions with thoughtful edits you’ll want to keep, post, and share.</p>
          <div className="hero-actions">
            <a className="button" href="#booking">Choose your time <span>→</span></a>
            <a className="text-link" href="#packages">View packages</a>
          </div>
          <div className="hero-proof">
            <div className="mini-portraits" aria-hidden="true"><span>J</span><span>♡</span><span>✦</span></div>
            <p><strong>Easy booking</strong><br />Pick a package, time, and pay online.</p>
          </div>
        </div>
        <div className="hero-art" aria-label="Joli's Photos brand artwork">
          <div className="photo-frame">
            <div className="frame-glow" />
            <div className="frame-copy"><span>Joli’s</span><strong>PHOTOS</strong><small>made with care</small></div>
          </div>
          <div className="polaroid"><span>YOUR STORY</span><b>beautifully kept</b></div>
          <div className="berry berry-one" /><div className="berry berry-two" /><div className="berry berry-three" />
          <p className="script-note">soft light · real smiles · lasting memories</p>
        </div>
      </section>

      <section className="packages" id="packages">
        <div className="section-heading">
          <div><p className="eyebrow">Simple, honest pricing</p><h2>Choose your session</h2></div>
          <p>Every package includes a relaxed shoot, professionally edited high-resolution photos, and an online gallery.</p>
        </div>
        <div className="package-grid">
          {packages.map((item) => (
            <article className={`package-card ${selectedId === item.id ? "selected" : ""}`} key={item.id}>
              <div className="card-top"><span>{item.category}</span>{item.id === "portrait-60" && <b>Most loved</b>}</div>
              <h3>{item.name}</h3>
              <p className="price"><sup>$</sup>{item.price}</p>
              <ul><li>{item.duration}</li><li>{item.photos} edited photos</li><li>Private online gallery</li></ul>
              <button onClick={() => choosePackage(item.id)}>Select session <span>→</span></button>
            </article>
          ))}
        </div>
      </section>

      <section className="booking-section" id="booking">
        <div className="booking-intro">
          <p className="eyebrow light">Book your session</p>
          <h2>A date to look<br />forward to.</h2>
          <p>Your selected time is reserved while you complete the booking. A {deposit === 15 ? "$15" : "30%"} deposit holds your spot.</p>
          <div className="steps">
            {[1, 2, 3].map((number) => <span className={step >= number ? "active" : ""} key={number}>{number}</span>)}
            <i />
          </div>
          <small>Questions? Message <a href="https://www.instagram.com/jolis.photos/" target="_blank" rel="noreferrer">@jolis.photos</a></small>
        </div>
        <div className="booking-panel">
          <div className="booking-summary">
            <span>{selected.name}</span><strong>${selected.price}</strong>
            <small>{selected.duration} · {selected.photos} edited photos</small>
          </div>

          {step <= 2 && (
            <div className="date-step">
              <label htmlFor="session-date">Choose a date</label>
              <input id="session-date" type="date" min={dateValue(1)} max={dateValue(120)} value={date} onChange={(event) => { setDate(event.target.value); setTime(""); setStep(2); }} />
              {date && <p className="date-label">Available on {prettyDate(date)}</p>}
              <div className="time-grid" aria-label="Available appointment times">
                {times.map((slot) => <button className={time === slot ? "active" : ""} onClick={() => setTime(slot)} key={slot}>{slot}</button>)}
              </div>
              <button className="button continue" onClick={continueToDetails}>Continue to details <span>→</span></button>
            </div>
          )}

          {step === 3 && status !== "success" && (
            <form className="details-form" onSubmit={submitBooking}>
              <button type="button" className="back" onClick={() => setStep(2)}>← Change date</button>
              <p className="chosen-time">{prettyDate(date)} at {time}</p>
              <div className="field-row"><label>Full name<input name="name" autoComplete="name" required placeholder="Your name" /></label><label>Phone<input name="phone" autoComplete="tel" required placeholder="(555) 123-4567" /></label></div>
              <label>Email address<input name="email" type="email" autoComplete="email" required placeholder="you@example.com" /></label>
              <label>Anything Joli should know?<textarea name="notes" rows={3} placeholder="Location ideas, occasion, number of people…" /></label>
              <div className="payment-line"><span>Deposit due today</span><strong>${deposit}</strong></div>
              <button className="button continue" disabled={status === "saving" || status === "payment"}>{status === "saving" ? "Reserving your time…" : status === "payment" ? "Opening secure payment…" : `Reserve & pay $${deposit}`} <span>→</span></button>
              <p className="secure">Secure card checkout · Remaining balance due on session day</p>
            </form>
          )}

          {message && <div className={`notice ${status}`}>{message}</div>}
        </div>
      </section>

      <section className="promise">
        <p>Come as you are.</p><h2>I’ll take care of the rest.</h2>
        <div><span>01</span><p><strong>Choose</strong><br />Pick the session that fits your story.</p><span>02</span><p><strong>Show up</strong><br />I’ll guide you so it never feels awkward.</p><span>03</span><p><strong>Keep it</strong><br />Receive polished photos in your gallery.</p></div>
      </section>

      <footer><a className="brand" href="#top"><span className="brand-mark">J</span><span>Joli’s <i>Photos</i></span></a><p>Portraits made personal.</p><a href="https://www.instagram.com/jolis.photos/" target="_blank" rel="noreferrer">@jolis.photos ↗</a></footer>
    </main>
  );
}
