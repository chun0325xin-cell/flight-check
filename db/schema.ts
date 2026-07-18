import { integer, sqliteTable, text, uniqueIndex } from "drizzle-orm/sqlite-core";

export const bookings = sqliteTable("bookings", {
  id: text("id").primaryKey(),
  packageId: text("package_id").notNull(),
  packageName: text("package_name").notNull(),
  sessionDate: text("session_date").notNull(),
  sessionTime: text("session_time").notNull(),
  customerName: text("customer_name").notNull(),
  email: text("email").notNull(),
  phone: text("phone").notNull(),
  notes: text("notes"),
  totalCents: integer("total_cents").notNull(),
  depositCents: integer("deposit_cents").notNull(),
  paymentStatus: text("payment_status").notNull().default("pending"),
  createdAt: text("created_at").notNull().default("CURRENT_TIMESTAMP"),
}, (table) => [uniqueIndex("booking_time_idx").on(table.sessionDate, table.sessionTime)]);
