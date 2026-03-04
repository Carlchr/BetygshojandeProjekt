-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Värd: 127.0.0.1
-- Tid vid skapande: 24 feb 2026 kl 20:04
-- Serverversion: 10.4.32-MariaDB
-- PHP-version: 8.0.30

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Databas: `forum_db`
--

-- --------------------------------------------------------

--
-- Tabellstruktur `posts`
--

CREATE TABLE `posts` (
  `id` int(100) NOT NULL AUTO_INCREMENT,
  `topic_id` int(100) NOT NULL, 
  `inlägg` varchar(100) NOT NULL,
  `datum` date NOT NULL,
  `username` varchar(50) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


----------------------------------------------------------

--
-- Tabellstruktur `topics`
--

CREATE TABLE `topics` (
  `id` int(100) NOT NULL,
  `rubrik` varchar(100) NOT NULL,
  `username` varchar(50) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumpning av Data i tabell `topics`
--

INSERT INTO `topics` (`id`, `rubrik`, `username`) VALUES
(1, 'Programmering', 'test');

-- --------------------------------------------------------

--
-- Tabellstruktur `users`
--

CREATE TABLE `users` (
  `id` int(50) NOT NULL,
  `name` varchar(50) NOT NULL,
  `username` varchar(50) NOT NULL,
  `email` varchar(100) NOT NULL,
  `password` varchar(300) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumpning av Data i tabell `users`
--

INSERT INTO `users` (`id`, `name`, `username`, `email`, `password`) VALUES
(1, '', 'test', '', 'scrypt:32768:8:1$OMxsVxOfU3Nh6KRi$3ee295a957fbb582a36d2ed4454b5984307d338ca5aeb8d2d5968ce1fa07ef48f41755bf961e63957a07c323ef18c2c89c1bac23acfa6d3fd306455286d3333b');

--
-- Index för dumpade tabeller
--

--
-- Index för tabell `topics`
--
ALTER TABLE `topics`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `rubrik` (`rubrik`);

--
-- Index för tabell `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `email` (`email`);

--
-- AUTO_INCREMENT för dumpade tabeller
--

--
-- AUTO_INCREMENT för tabell `topics`
--
ALTER TABLE `topics`
  MODIFY `id` int(100) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT för tabell `users`
--
ALTER TABLE `users`
  MODIFY `id` int(50) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
