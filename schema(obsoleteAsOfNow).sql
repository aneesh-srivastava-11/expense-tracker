-- Create database
CREATE DATABASE tracker;
USE tracker;
-- Users table
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL
);
-- Expenses table
CREATE TABLE expenses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    amount DECIMAL(10,2),
    date DATE,
    user_id INT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
