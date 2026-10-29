CREATE DATABASE poc_data;
\connect poc_data

CREATE TABLE IF NOT EXISTS public.poc_orders (
    order_id INTEGER PRIMARY KEY,
    order_date DATE NOT NULL,
    region TEXT NOT NULL,
    product TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    revenue NUMERIC(10, 2) NOT NULL
);

INSERT INTO public.poc_orders
    (order_id, order_date, region, product, quantity, revenue)
VALUES
    (1, '2025-01-05', 'North', 'Widget A', 12, 240.00),
    (2, '2025-01-07', 'South', 'Widget B', 8, 200.00),
    (3, '2025-01-12', 'East', 'Widget A', 15, 300.00),
    (4, '2025-01-18', 'West', 'Widget C', 5, 175.00),
    (5, '2025-02-02', 'North', 'Widget B', 11, 275.00),
    (6, '2025-02-10', 'South', 'Widget C', 9, 315.00)
ON CONFLICT (order_id) DO NOTHING;
