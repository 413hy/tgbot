-- MySQL schema for TixBot
-- Recommended: MySQL 8.x (5.7+ should also work)
-- Engine: InnoDB, charset: utf8mb4

CREATE DATABASE IF NOT EXISTS tixbot
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_0900_ai_ci;

USE tixbot;

-- 1) Users (points)
CREATE TABLE IF NOT EXISTS tg_users (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  tg_id         BIGINT NOT NULL UNIQUE,
  username      VARCHAR(255) NULL,
  first_name    VARCHAR(255) NULL,
  last_name     VARCHAR(255) NULL,
  points        BIGINT NOT NULL DEFAULT 0,
  email         VARCHAR(255) NULL,
  whmcs_client_id BIGINT NULL,
  created_at    DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at    DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2) Chats (groups/supergroups)
CREATE TABLE IF NOT EXISTS tg_chats (
  id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  chat_id     BIGINT NOT NULL UNIQUE,
  title       VARCHAR(255) NULL,
  type        VARCHAR(32) NULL,
  created_at  DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3) Private-chat context: which target group is bound for /tixnew
CREATE TABLE IF NOT EXISTS user_chat_context (
  id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  tg_user_id  BIGINT NOT NULL UNIQUE,
  chat_id     BIGINT NOT NULL,
  updated_at  DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  INDEX idx_ucc_chat (chat_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4) Raffles
CREATE TABLE IF NOT EXISTS raffles (
  id                   BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  code                 VARCHAR(32) NOT NULL UNIQUE,
  creator_tg_id         BIGINT NOT NULL,
  target_chat_id        BIGINT NOT NULL,

  title                VARCHAR(255) NOT NULL DEFAULT '',
  description           TEXT NULL,

  join_mode             VARCHAR(16) NOT NULL DEFAULT 'button',

  cost_points           BIGINT NOT NULL DEFAULT 0,
  required_chats        JSON NOT NULL,
  min_messages          INT NOT NULL DEFAULT 0,

  draw_mode             VARCHAR(16) NOT NULL DEFAULT 'time',
  draw_at               DATETIME(3) NULL,
  min_participants      INT NOT NULL DEFAULT 0,

  status                VARCHAR(16) NOT NULL DEFAULT 'draft',
  published_message_id  BIGINT NULL,
  pinned_message_id     BIGINT NULL,
  draw_pinned_message_id BIGINT NULL,

  draw_block_hash       CHAR(64) NULL,
  draw_block_height     BIGINT NULL,
  drawn_at              DATETIME(3) NULL,

  next_participant_no   BIGINT UNSIGNED NOT NULL DEFAULT 1,

  created_at            DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at            DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),

  INDEX idx_raffles_creator (creator_tg_id),
  INDEX idx_raffles_target_chat (target_chat_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- NOTE: For required_chats, insert with JSON_ARRAY() for empty list.

-- 5) Prizes
CREATE TABLE IF NOT EXISTS raffle_prizes (
  id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  raffle_id   BIGINT UNSIGNED NOT NULL,
  prize_type  VARCHAR(16) NOT NULL DEFAULT 'custom',
  prize_name  VARCHAR(255) NOT NULL,
  quantity    INT NOT NULL DEFAULT 1,
  points_amount BIGINT NULL,
  custom_label VARCHAR(255) NULL,
  INDEX idx_prizes_raffle (raffle_id),
  CONSTRAINT fk_prizes_raffle
    FOREIGN KEY (raffle_id) REFERENCES raffles(id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- 6) Participants
CREATE TABLE IF NOT EXISTS raffle_participants (
  id             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  raffle_id      BIGINT UNSIGNED NOT NULL,
  tg_id          BIGINT NOT NULL,
  username       VARCHAR(255) NULL,
  participant_no BIGINT UNSIGNED NOT NULL,
  status         VARCHAR(16) NOT NULL DEFAULT 'joined',
  joined_at      DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

  -- Receipt message in group after user confirms participation
  receipt_chat_id    BIGINT NULL,
  receipt_message_id BIGINT NULL,
  receipt_deleted_at DATETIME(3) NULL,

  hash_hex       CHAR(64) NULL,
  score          BIGINT UNSIGNED NULL,
  win_prize      VARCHAR(255) NULL,
  win_rank       INT NULL,
  UNIQUE KEY uk_participant_user (raffle_id, tg_id),
  UNIQUE KEY uk_participant_no (raffle_id, participant_no),
  INDEX idx_participants_raffle (raffle_id),
  INDEX idx_participants_score (raffle_id, score),
  CONSTRAINT fk_participants_raffle
    FOREIGN KEY (raffle_id) REFERENCES raffles(id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7) Points ledger
CREATE TABLE IF NOT EXISTS points_ledger (
  id         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  tg_id      BIGINT NOT NULL,
  delta      BIGINT NOT NULL,
  reason     VARCHAR(64) NOT NULL,
  ref_type   VARCHAR(32) NULL,
  ref_code   VARCHAR(32) NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  INDEX idx_ledger_tg (tg_id),
  INDEX idx_ledger_ref (ref_type, ref_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 8) Chat message stats (must be maintained by the bot)
CREATE TABLE IF NOT EXISTS chat_user_stats (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  chat_id         BIGINT NOT NULL,
  tg_id           BIGINT NOT NULL,
  message_count   BIGINT NOT NULL DEFAULT 0,
  last_message_at DATETIME(3) NULL,
  UNIQUE KEY uk_stats (chat_id, tg_id),
  INDEX idx_stats_chat (chat_id),
  INDEX idx_stats_user (tg_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
