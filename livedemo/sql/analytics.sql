CREATE TABLE analytics_visits (
  id            serial PRIMARY KEY,
  visitor_id    text NOT NULL,
  timestamp     timestamptz NOT NULL DEFAULT now(),
  path          text NOT NULL,
  referrer      text,
  user_agent    text
);

CREATE TABLE analytics_runs (
  id            serial PRIMARY KEY,
  run_id        text NOT NULL UNIQUE,
  visitor_id    text,
  timestamp     timestamptz NOT NULL DEFAULT now(),
  query         text NOT NULL,
  date          text NOT NULL,
  status        text NOT NULL DEFAULT 'running',
  cost          numeric
);

CREATE INDEX idx_visits_timestamp ON analytics_visits (timestamp);
CREATE INDEX idx_visits_visitor ON analytics_visits (visitor_id);
CREATE INDEX idx_runs_timestamp ON analytics_runs (timestamp);
