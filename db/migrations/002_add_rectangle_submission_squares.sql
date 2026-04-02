CREATE TABLE IF NOT EXISTS submission_rectangle_squares (
  submission_id bigint NOT NULL,
  idx integer NOT NULL,
  cx double precision NOT NULL,
  cy double precision NOT NULL,
  ux double precision NOT NULL,
  uy double precision NOT NULL,
  cx_q bigint NOT NULL,
  cy_q bigint NOT NULL,
  ux_q bigint NOT NULL,
  uy_q bigint NOT NULL,
  width double precision NOT NULL DEFAULT 56,
  height double precision NOT NULL DEFAULT 56,
  pinned boolean NOT NULL DEFAULT false
);

ALTER TABLE submission_rectangle_squares
  ADD COLUMN IF NOT EXISTS width double precision NOT NULL DEFAULT 56;

ALTER TABLE submission_rectangle_squares
  ADD COLUMN IF NOT EXISTS height double precision NOT NULL DEFAULT 56;

ALTER TABLE submission_rectangle_squares
  ADD CONSTRAINT submission_rectangle_squares_pk PRIMARY KEY (submission_id, idx);

ALTER TABLE submission_rectangle_squares
  ADD CONSTRAINT submission_rectangle_squares_sub_fk
  FOREIGN KEY (submission_id) REFERENCES submissions (id);
