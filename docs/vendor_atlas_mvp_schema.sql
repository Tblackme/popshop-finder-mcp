-- Vendor Atlas MVP marketplace schema
-- Source-of-truth table names and columns requested for the 3-sided marketplace.
-- In this repo's SQLite implementation, UUID values are stored as TEXT.

CREATE TABLE users (
    id uuid PRIMARY KEY,
    email text UNIQUE NOT NULL,
    username text NOT NULL,
    role text NOT NULL CHECK (role IN ('vendor', 'organizer', 'shopper')),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE vendors (
    id uuid PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    business_name text NOT NULL,
    description text,
    category text,
    location text,
    instagram_url text,
    website_url text,
    shopify_url text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE events (
    id uuid PRIMARY KEY,
    organizer_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title text NOT NULL,
    description text,
    category text,
    location text,
    start_date timestamptz NOT NULL,
    end_date timestamptz NOT NULL,
    vendor_fee numeric,
    application_url text,
    is_claimed boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE event_applications (
    id uuid PRIMARY KEY,
    event_id uuid NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    vendor_id uuid NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    status text NOT NULL CHECK (status IN ('applied', 'accepted', 'rejected', 'waitlisted')),
    message text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE saved_events (
    id uuid PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_id uuid NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE followed_vendors (
    id uuid PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    vendor_id uuid NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE vendor_event_stats (
    id uuid PRIMARY KEY,
    vendor_id uuid NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    event_id uuid NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    revenue numeric,
    expenses numeric,
    vendor_fee numeric,
    profit numeric,
    notes text,
    created_at timestamptz NOT NULL DEFAULT now()
);
