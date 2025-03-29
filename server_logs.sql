-- Step 1: Create the database
CREATE DATABASE IF NOT EXISTS server_monitoring;

-- Step 2: Use the database
USE server_monitoring;

-- Step 3: Create the table
CREATE TABLE IF NOT EXISTS server_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    server_uuid VARCHAR(50),
    name VARCHAR(255),
    filename VARCHAR(255),
    updatableBy TEXT,
    component TEXT,
    state VARCHAR(50),
    timestamp DATETIME
);

-- Step 4: Verify table creation
SHOW TABLES; 
DESCRIBE server_logs;
