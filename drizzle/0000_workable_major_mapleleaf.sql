CREATE TABLE `bookings` (
	`id` text PRIMARY KEY NOT NULL,
	`package_id` text NOT NULL,
	`package_name` text NOT NULL,
	`session_date` text NOT NULL,
	`session_time` text NOT NULL,
	`customer_name` text NOT NULL,
	`email` text NOT NULL,
	`phone` text NOT NULL,
	`notes` text,
	`total_cents` integer NOT NULL,
	`deposit_cents` integer NOT NULL,
	`payment_status` text DEFAULT 'pending' NOT NULL,
	`created_at` text DEFAULT 'CURRENT_TIMESTAMP' NOT NULL
);
--> statement-breakpoint
CREATE UNIQUE INDEX `booking_time_idx` ON `bookings` (`session_date`,`session_time`);