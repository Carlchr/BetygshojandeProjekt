-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Värd: 127.0.0.1
-- Tid vid skapande: 06 mars 2026 kl 09:29
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
  `id` int(100) NOT NULL,
  `topic_id` int(100) NOT NULL,
  `inlägg` varchar(100) NOT NULL,
  `datum` date NOT NULL,
  `username` varchar(50) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumpning av Data i tabell `posts`
--

INSERT INTO `posts` (`id`, `topic_id`, `inlägg`, `datum`, `username`) VALUES
(1, 1, 'baba ganoush', '2026-03-04', 'test'),
(2, 1, 'vaaa vad sjukt', '2026-03-04', 'test'),
(3, 0, '3633643443643', '2026-03-05', 'test');

-- --------------------------------------------------------

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
(1, 'Programmering', 'test'),
(2, '456', 'test');

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
(1, '', 'test', '', 'scrypt:32768:8:1$OMxsVxOfU3Nh6KRi$3ee295a957fbb582a36d2ed4454b5984307d338ca5aeb8d2d5968ce1fa07ef48f41755bf961e63957a07c323ef18c2c89c1bac23acfa6d3fd306455286d3333b'),
(0, '', 'Admin', '', 'scrypt:32768:8:1$K2dXepR8Vnk5Oihd$eaf8b6e0b8e9b3d77437419ab65344b6fd3b604f7d965bb1eb07f0f2e17b18471df5ebac5c8d4ebe7b51b725d82362e1008a186c0fcf7be8ec698c421efe3d2c');

--
-- Index för dumpade tabeller
--

--
-- Index för tabell `posts`
--
ALTER TABLE `posts`
  ADD PRIMARY KEY (`id`);

--
-- Index för tabell `topics`
--
ALTER TABLE `topics`
  ADD PRIMARY KEY (`id`);

--
-- AUTO_INCREMENT för dumpade tabeller
--

--
-- AUTO_INCREMENT för tabell `posts`
--
ALTER TABLE `posts`
  MODIFY `id` int(100) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT för tabell `topics`
--
ALTER TABLE `topics`
  MODIFY `id` int(100) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
