/*
 Navicat Premium Dump SQL

 Source Server         : pzyta
 Source Server Type    : MySQL
 Source Server Version : 50744 (5.7.44)
 Source Host           : 127.0.0.1:3306
 Source Schema         : tgbot

 Target Server Type    : MySQL
 Target Server Version : 50744 (5.7.44)
 File Encoding         : 65001

 Date: 29/01/2026 11:13:51
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for change_email_codes
-- ----------------------------
DROP TABLE IF EXISTS `change_email_codes`;
CREATE TABLE `change_email_codes`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `tg_id` bigint(20) NOT NULL,
  `new_email` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `code` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `expires_at` datetime NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uniq_tg_id`(`tg_id`) USING BTREE,
  INDEX `idx_tg_id`(`tg_id`) USING BTREE,
  INDEX `idx_expires`(`expires_at`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 3 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Records of change_email_codes
-- ----------------------------
INSERT INTO `change_email_codes` VALUES (2, 6322070620, 'chisgmsinge@gmail.com', '668116', '2026-01-28 17:40:22', '2026-01-28 17:30:22');

-- ----------------------------
-- Table structure for exchange_logs
-- ----------------------------
DROP TABLE IF EXISTS `exchange_logs`;
CREATE TABLE `exchange_logs`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `tg_id` bigint(20) NULL DEFAULT NULL,
  `exchange_date` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `points_deducted` int(11) NULL DEFAULT NULL,
  `item_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `details` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `tg_id`(`tg_id`) USING BTREE,
  CONSTRAINT `exchange_logs_ibfk_1` FOREIGN KEY (`tg_id`) REFERENCES `users` (`tg_id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 51 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Records of exchange_logs
-- ----------------------------
INSERT INTO `exchange_logs` VALUES (43, 6977085303, '2026-01-14 13:14:56', 100, 'NAT 1个月续期', '{\"days\": 30}');
INSERT INTO `exchange_logs` VALUES (44, 761935676, '2026-01-14 16:15:37', 100, 'NAT 1个月续期', '{\"days\": 30}');
INSERT INTO `exchange_logs` VALUES (45, 7462224254, '2026-01-18 00:09:05', 100, 'NAT 1个月续期', '{\"days\": 30}');
INSERT INTO `exchange_logs` VALUES (46, 797391680, '2026-01-19 04:13:56', 100, 'NAT 1个月续期', '{\"days\": 30}');
INSERT INTO `exchange_logs` VALUES (47, 1829581222, '2026-01-19 16:43:01', 100, 'NAT 1个月续期', '{\"days\": 30}');
INSERT INTO `exchange_logs` VALUES (48, 7896336520, '2026-01-23 08:55:31', 100, 'NAT 1个月续期', '{\"days\": 30}');
INSERT INTO `exchange_logs` VALUES (49, 5514301656, '2026-01-27 09:26:13', 100, 'NAT 1个月续期', '{\"days\": 30}');
INSERT INTO `exchange_logs` VALUES (50, 761935676, '2026-01-29 09:37:49', 100, 'NAT 1个月续期', '{\"days\": 30}');

-- ----------------------------
-- Table structure for exchange_options
-- ----------------------------
DROP TABLE IF EXISTS `exchange_options`;
CREATE TABLE `exchange_options`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `points_required` int(11) NOT NULL,
  `type` enum('nat_renew','discount_code') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `details` json NULL,
  `is_active` tinyint(1) NULL DEFAULT 1,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 8 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Records of exchange_options
-- ----------------------------
INSERT INTO `exchange_options` VALUES (1, 'NAT 1个月续期', 100, 'nat_renew', '{\"days\": 30}', 1, '2025-12-26 02:40:21', '2025-12-26 02:40:21');
INSERT INTO `exchange_options` VALUES (4, 'NAT 3个月续期', 250, 'nat_renew', '{\"days\": 90}', 1, '2025-12-26 02:40:21', '2025-12-26 02:40:21');
INSERT INTO `exchange_options` VALUES (7, '1美元优惠码', 500, 'discount_code', '{\"amount\": 1}', 1, '2025-12-26 02:40:21', '2025-12-26 04:23:10');

-- ----------------------------
-- Table structure for group_message_counts
-- ----------------------------
DROP TABLE IF EXISTS `group_message_counts`;
CREATE TABLE `group_message_counts`  (
  `chat_id` bigint(20) NOT NULL,
  `tg_id` bigint(20) NOT NULL,
  `message_count` int(11) NOT NULL DEFAULT 0,
  `last_message_at` datetime NOT NULL,
  PRIMARY KEY (`chat_id`, `tg_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Records of group_message_counts
-- ----------------------------

-- ----------------------------
-- Table structure for points_ledger
-- ----------------------------
DROP TABLE IF EXISTS `points_ledger`;
CREATE TABLE `points_ledger`  (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `tg_id` bigint(20) NOT NULL,
  `delta` bigint(20) NOT NULL,
  `reason` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `ref_type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `ref_code` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `created_at` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_ledger_tg`(`tg_id`) USING BTREE,
  INDEX `idx_ledger_ref`(`ref_type`, `ref_code`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 8 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Records of points_ledger
-- ----------------------------

-- ----------------------------
-- Table structure for prize_wins
-- ----------------------------
DROP TABLE IF EXISTS `prize_wins`;
CREATE TABLE `prize_wins`  (
  `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `raffle_code` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `raffle_title` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `user_id` bigint(20) UNSIGNED NULL DEFAULT NULL,
  `tg_id` bigint(20) NOT NULL,
  `email` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `whmcs_client_id` bigint(20) NULL DEFAULT NULL,
  `win_rank` int(11) NOT NULL,
  `participant_no` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `prize_type` enum('points','vps','nat','discount_code','other') CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `prize_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `quantity` int(11) NOT NULL DEFAULT 1,
  `points_amount` bigint(20) NULL DEFAULT NULL,
  `status` enum('pending','fulfilled','canceled') CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'pending',
  `auto_credit` tinyint(1) NOT NULL DEFAULT 0,
  `note` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `meta` json NULL,
  `created_at` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  `fulfilled_at` datetime(3) NULL DEFAULT NULL,
  `operator_tg_id` bigint(20) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_raffle_rank`(`raffle_code`, `win_rank`) USING BTREE,
  UNIQUE INDEX `uk_raffle_tg`(`raffle_code`, `tg_id`) USING BTREE,
  INDEX `idx_tg_id`(`tg_id`) USING BTREE,
  INDEX `idx_raffle`(`raffle_code`) USING BTREE,
  INDEX `idx_status`(`status`) USING BTREE,
  INDEX `idx_type_status`(`prize_type`, `status`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 11 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Records of prize_wins
-- ----------------------------
INSERT INTO `prize_wins` VALUES (7, 'L1768284397864', '抽奖 L1768284397864', NULL, 6977085303, '3079980988@qq.com', 2, 1, '70517715', 'points', '10 积分', 1, 10, 'fulfilled', 1, 'tixbot raffle draw', '{\"source\": \"tixbot\", \"raffle_code\": \"L1768284397864\"}', '2026-01-13 14:10:04.000', '2026-01-13 14:10:04.000', NULL);
INSERT INTO `prize_wins` VALUES (8, 'L1768358285817', '抽奖 L1768358285817', NULL, 6322070620, 'hey.04138714@gmail.com', 7, 1, '49409268', 'points', '10 积分', 1, 10, 'fulfilled', 1, 'tixbot raffle draw', '{\"source\": \"tixbot\", \"raffle_code\": \"L1768358285817\"}', '2026-01-14 10:41:01.000', '2026-01-14 10:41:01.000', NULL);
INSERT INTO `prize_wins` VALUES (9, 'L1768358689909', '抽奖 L1768358689909', NULL, 6977085303, '3079980988@qq.com', 2, 1, '65055956', 'points', '10 积分', 1, 10, 'fulfilled', 1, 'tixbot raffle draw', '{\"source\": \"tixbot\", \"raffle_code\": \"L1768358689909\"}', '2026-01-14 10:45:57.000', '2026-01-14 10:45:57.000', NULL);
INSERT INTO `prize_wins` VALUES (10, 'L1768358689909', '抽奖 L1768358689909', NULL, 6322070620, 'hey.04138714@gmail.com', 7, 2, '61762379', 'vps', 'lax', 1, NULL, 'pending', 0, 'tixbot raffle draw', '{\"source\": \"tixbot\", \"raffle_code\": \"L1768358689909\"}', '2026-01-14 10:45:57.000', NULL, NULL);

-- ----------------------------
-- Table structure for raffle_entries
-- ----------------------------
DROP TABLE IF EXISTS `raffle_entries`;
CREATE TABLE `raffle_entries`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `raffle_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `tg_id` bigint(20) NOT NULL,
  `username` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `status` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT 'joined',
  `joined_at` datetime NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `unique_entry`(`raffle_id`, `tg_id`) USING BTREE,
  CONSTRAINT `raffle_entries_ibfk_1` FOREIGN KEY (`raffle_id`) REFERENCES `raffles` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Records of raffle_entries
-- ----------------------------

-- ----------------------------
-- Table structure for raffle_groups
-- ----------------------------
DROP TABLE IF EXISTS `raffle_groups`;
CREATE TABLE `raffle_groups`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `raffle_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `group_id` bigint(20) NOT NULL,
  `group_username` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `group_title` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `min_messages` int(11) NULL DEFAULT 0,
  `hide_link` tinyint(1) NULL DEFAULT 0,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `raffle_id`(`raffle_id`) USING BTREE,
  CONSTRAINT `raffle_groups_ibfk_1` FOREIGN KEY (`raffle_id`) REFERENCES `raffles` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Records of raffle_groups
-- ----------------------------

-- ----------------------------
-- Table structure for raffle_prizes
-- ----------------------------
DROP TABLE IF EXISTS `raffle_prizes`;
CREATE TABLE `raffle_prizes`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `raffle_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `quantity` int(11) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `raffle_id`(`raffle_id`) USING BTREE,
  CONSTRAINT `raffle_prizes_ibfk_1` FOREIGN KEY (`raffle_id`) REFERENCES `raffles` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Records of raffle_prizes
-- ----------------------------

-- ----------------------------
-- Table structure for raffles
-- ----------------------------
DROP TABLE IF EXISTS `raffles`;
CREATE TABLE `raffles`  (
  `id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `chat_id` bigint(20) NOT NULL,
  `creator_tg_id` bigint(20) NOT NULL,
  `title` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL,
  `participation_text` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL,
  `required_groups` json NULL,
  `min_group_messages` int(11) NULL DEFAULT 0,
  `points_cost` int(11) NULL DEFAULT 0,
  `draw_mode` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT 'scheduled',
  `draw_at` datetime NULL DEFAULT NULL,
  `min_participants` int(11) NULL DEFAULT 0,
  `draw_hash` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT NULL,
  `status` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NULL DEFAULT 'open',
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Records of raffles
-- ----------------------------

-- ----------------------------
-- Table structure for sign_logs
-- ----------------------------
DROP TABLE IF EXISTS `sign_logs`;
CREATE TABLE `sign_logs`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `tg_id` bigint(20) NULL DEFAULT NULL,
  `sign_date` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `points_added` int(11) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `tg_id`(`tg_id`) USING BTREE,
  CONSTRAINT `sign_logs_ibfk_1` FOREIGN KEY (`tg_id`) REFERENCES `users` (`tg_id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 578 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Records of sign_logs
-- ----------------------------
INSERT INTO `sign_logs` VALUES (122, 508288539, '2026-01-13 14:08:20', 5);
INSERT INTO `sign_logs` VALUES (123, 797391680, '2026-01-13 14:41:57', 9);
INSERT INTO `sign_logs` VALUES (124, 7827117448, '2026-01-13 14:43:20', 7);
INSERT INTO `sign_logs` VALUES (125, 1316336246, '2026-01-13 14:50:23', 9);
INSERT INTO `sign_logs` VALUES (126, 6977085303, '2026-01-13 14:51:47', 7);
INSERT INTO `sign_logs` VALUES (127, 1829581222, '2026-01-13 14:56:02', 8);
INSERT INTO `sign_logs` VALUES (128, 924854603, '2026-01-13 15:10:19', 7);
INSERT INTO `sign_logs` VALUES (129, 5514301656, '2026-01-13 15:16:54', 6);
INSERT INTO `sign_logs` VALUES (130, 7896336520, '2026-01-13 15:53:06', 7);
INSERT INTO `sign_logs` VALUES (131, 5426150478, '2026-01-13 18:10:34', 10);
INSERT INTO `sign_logs` VALUES (132, 5056439343, '2026-01-13 20:13:11', 4);
INSERT INTO `sign_logs` VALUES (133, 646561495, '2026-01-13 23:36:37', 10);
INSERT INTO `sign_logs` VALUES (134, 7640872861, '2026-01-14 00:00:41', 7);
INSERT INTO `sign_logs` VALUES (135, 7698928816, '2026-01-14 00:01:01', 5);
INSERT INTO `sign_logs` VALUES (136, 5514301656, '2026-01-14 00:07:31', 8);
INSERT INTO `sign_logs` VALUES (137, 924854603, '2026-01-14 00:15:14', 6);
INSERT INTO `sign_logs` VALUES (138, 1829581222, '2026-01-14 00:30:35', 8);
INSERT INTO `sign_logs` VALUES (139, 1316336246, '2026-01-14 00:49:16', 6);
INSERT INTO `sign_logs` VALUES (140, 646561495, '2026-01-14 01:01:22', 10);
INSERT INTO `sign_logs` VALUES (141, 5056439343, '2026-01-14 01:47:18', 9);
INSERT INTO `sign_logs` VALUES (142, 797391680, '2026-01-14 03:03:18', 8);
INSERT INTO `sign_logs` VALUES (143, 761935676, '2026-01-14 08:11:07', 10);
INSERT INTO `sign_logs` VALUES (144, 7896336520, '2026-01-14 09:13:08', 9);
INSERT INTO `sign_logs` VALUES (145, 8061873913, '2026-01-14 11:45:29', 6);
INSERT INTO `sign_logs` VALUES (146, 508288539, '2026-01-14 13:14:59', 5);
INSERT INTO `sign_logs` VALUES (147, 2051848341, '2026-01-14 13:19:54', 6);
INSERT INTO `sign_logs` VALUES (148, 1794591642, '2026-01-14 17:35:38', 10);
INSERT INTO `sign_logs` VALUES (149, 7827117448, '2026-01-14 21:42:37', 5);
INSERT INTO `sign_logs` VALUES (150, 7698928816, '2026-01-15 00:01:01', 10);
INSERT INTO `sign_logs` VALUES (151, 1316336246, '2026-01-15 00:01:49', 5);
INSERT INTO `sign_logs` VALUES (152, 7640872861, '2026-01-15 00:21:20', 8);
INSERT INTO `sign_logs` VALUES (153, 1829581222, '2026-01-15 00:36:18', 8);
INSERT INTO `sign_logs` VALUES (154, 797391680, '2026-01-15 00:50:04', 5);
INSERT INTO `sign_logs` VALUES (155, 5514301656, '2026-01-15 00:54:02', 8);
INSERT INTO `sign_logs` VALUES (156, 6977085303, '2026-01-15 00:54:31', 10);
INSERT INTO `sign_logs` VALUES (157, 7462224254, '2026-01-15 02:15:28', 7);
INSERT INTO `sign_logs` VALUES (158, 646561495, '2026-01-15 02:46:08', 7);
INSERT INTO `sign_logs` VALUES (159, 761935676, '2026-01-15 08:02:24', 6);
INSERT INTO `sign_logs` VALUES (160, 1794591642, '2026-01-15 08:25:54', 7);
INSERT INTO `sign_logs` VALUES (161, 7896336520, '2026-01-15 08:35:47', 6);
INSERT INTO `sign_logs` VALUES (162, 7827117448, '2026-01-15 11:18:20', 10);
INSERT INTO `sign_logs` VALUES (163, 8061873913, '2026-01-15 11:33:43', 7);
INSERT INTO `sign_logs` VALUES (164, 5319014516, '2026-01-15 12:16:48', 5);
INSERT INTO `sign_logs` VALUES (165, 924854603, '2026-01-15 14:21:25', 9);
INSERT INTO `sign_logs` VALUES (166, 508288539, '2026-01-15 21:32:07', 7);
INSERT INTO `sign_logs` VALUES (167, 7698928816, '2026-01-16 00:01:01', 4);
INSERT INTO `sign_logs` VALUES (168, 5514301656, '2026-01-16 00:03:06', 10);
INSERT INTO `sign_logs` VALUES (169, 7640872861, '2026-01-16 00:08:29', 10);
INSERT INTO `sign_logs` VALUES (170, 761935676, '2026-01-16 00:12:46', 6);
INSERT INTO `sign_logs` VALUES (171, 646561495, '2026-01-16 00:16:43', 6);
INSERT INTO `sign_logs` VALUES (172, 1316336246, '2026-01-16 00:22:06', 4);
INSERT INTO `sign_logs` VALUES (173, 1829581222, '2026-01-16 00:42:00', 10);
INSERT INTO `sign_logs` VALUES (174, 7462224254, '2026-01-16 02:40:05', 9);
INSERT INTO `sign_logs` VALUES (175, 8061873913, '2026-01-16 07:10:48', 8);
INSERT INTO `sign_logs` VALUES (176, 7896336520, '2026-01-16 08:45:52', 5);
INSERT INTO `sign_logs` VALUES (177, 797391680, '2026-01-16 13:12:28', 5);
INSERT INTO `sign_logs` VALUES (178, 508288539, '2026-01-16 13:41:05', 8);
INSERT INTO `sign_logs` VALUES (179, 2051848341, '2026-01-16 21:11:00', 4);
INSERT INTO `sign_logs` VALUES (180, 5056439343, '2026-01-16 23:04:33', 4);
INSERT INTO `sign_logs` VALUES (181, 7698928816, '2026-01-17 00:01:01', 9);
INSERT INTO `sign_logs` VALUES (182, 5514301656, '2026-01-17 00:04:24', 8);
INSERT INTO `sign_logs` VALUES (183, 508288539, '2026-01-17 00:10:49', 8);
INSERT INTO `sign_logs` VALUES (184, 761935676, '2026-01-17 00:12:24', 10);
INSERT INTO `sign_logs` VALUES (185, 7640872861, '2026-01-17 00:12:37', 5);
INSERT INTO `sign_logs` VALUES (186, 1829581222, '2026-01-17 00:31:41', 9);
INSERT INTO `sign_logs` VALUES (187, 7827117448, '2026-01-17 01:14:12', 10);
INSERT INTO `sign_logs` VALUES (188, 646561495, '2026-01-17 01:34:33', 9);
INSERT INTO `sign_logs` VALUES (189, 1316336246, '2026-01-17 02:39:08', 10);
INSERT INTO `sign_logs` VALUES (190, 797391680, '2026-01-17 03:24:14', 4);
INSERT INTO `sign_logs` VALUES (191, 7462224254, '2026-01-17 03:25:34', 5);
INSERT INTO `sign_logs` VALUES (192, 7896336520, '2026-01-17 08:36:42', 8);
INSERT INTO `sign_logs` VALUES (193, 924854603, '2026-01-17 12:33:44', 5);
INSERT INTO `sign_logs` VALUES (194, 6977085303, '2026-01-17 15:14:09', 7);
INSERT INTO `sign_logs` VALUES (195, 7698928816, '2026-01-18 00:01:01', 8);
INSERT INTO `sign_logs` VALUES (196, 5514301656, '2026-01-18 00:04:08', 5);
INSERT INTO `sign_logs` VALUES (197, 7462224254, '2026-01-18 00:06:39', 6);
INSERT INTO `sign_logs` VALUES (198, 797391680, '2026-01-18 00:07:37', 6);
INSERT INTO `sign_logs` VALUES (199, 7640872861, '2026-01-18 00:25:44', 10);
INSERT INTO `sign_logs` VALUES (200, 1829581222, '2026-01-18 01:12:56', 6);
INSERT INTO `sign_logs` VALUES (201, 7827117448, '2026-01-18 01:45:22', 6);
INSERT INTO `sign_logs` VALUES (202, 1316336246, '2026-01-18 02:33:04', 5);
INSERT INTO `sign_logs` VALUES (203, 6914122934, '2026-01-18 07:22:38', 4);
INSERT INTO `sign_logs` VALUES (204, 761935676, '2026-01-18 08:34:59', 5);
INSERT INTO `sign_logs` VALUES (205, 924854603, '2026-01-18 10:34:26', 4);
INSERT INTO `sign_logs` VALUES (206, 508288539, '2026-01-18 13:30:49', 7);
INSERT INTO `sign_logs` VALUES (207, 7896336520, '2026-01-18 20:18:02', 9);
INSERT INTO `sign_logs` VALUES (208, 646561495, '2026-01-18 21:44:44', 9);
INSERT INTO `sign_logs` VALUES (209, 5514301656, '2026-01-19 00:00:12', 7);
INSERT INTO `sign_logs` VALUES (210, 7698928816, '2026-01-19 00:01:01', 6);
INSERT INTO `sign_logs` VALUES (211, 761935676, '2026-01-19 00:10:45', 9);
INSERT INTO `sign_logs` VALUES (212, 1829581222, '2026-01-19 00:31:45', 4);
INSERT INTO `sign_logs` VALUES (213, 7462224254, '2026-01-19 01:26:08', 6);
INSERT INTO `sign_logs` VALUES (214, 797391680, '2026-01-19 04:12:21', 4);
INSERT INTO `sign_logs` VALUES (215, 2051848341, '2026-01-19 07:06:09', 10);
INSERT INTO `sign_logs` VALUES (216, 6914122934, '2026-01-19 07:17:18', 9);
INSERT INTO `sign_logs` VALUES (217, 8061873913, '2026-01-19 08:18:27', 6);
INSERT INTO `sign_logs` VALUES (218, 7896336520, '2026-01-19 10:37:54', 7);
INSERT INTO `sign_logs` VALUES (219, 1316336246, '2026-01-19 13:46:36', 10);
INSERT INTO `sign_logs` VALUES (220, 646561495, '2026-01-19 13:51:38', 7);
INSERT INTO `sign_logs` VALUES (221, 924854603, '2026-01-19 16:26:54', 9);
INSERT INTO `sign_logs` VALUES (222, 5056439343, '2026-01-19 16:45:18', 5);
INSERT INTO `sign_logs` VALUES (223, 508288539, '2026-01-19 18:22:11', 8);
INSERT INTO `sign_logs` VALUES (224, 7640872861, '2026-01-19 21:40:47', 6);
INSERT INTO `sign_logs` VALUES (225, 7698928816, '2026-01-20 00:01:01', 10);
INSERT INTO `sign_logs` VALUES (226, 5514301656, '2026-01-20 00:02:46', 7);
INSERT INTO `sign_logs` VALUES (227, 797391680, '2026-01-20 00:13:17', 8);
INSERT INTO `sign_logs` VALUES (228, 1829581222, '2026-01-20 00:30:00', 4);
INSERT INTO `sign_logs` VALUES (229, 7462224254, '2026-01-20 02:12:58', 8);
INSERT INTO `sign_logs` VALUES (230, 7640872861, '2026-01-20 02:59:37', 4);
INSERT INTO `sign_logs` VALUES (231, 8061873913, '2026-01-20 06:55:37', 5);
INSERT INTO `sign_logs` VALUES (232, 6914122934, '2026-01-20 07:11:29', 5);
INSERT INTO `sign_logs` VALUES (233, 924854603, '2026-01-20 08:32:31', 9);
INSERT INTO `sign_logs` VALUES (234, 7896336520, '2026-01-20 09:02:48', 6);
INSERT INTO `sign_logs` VALUES (235, 1316336246, '2026-01-20 09:16:13', 7);
INSERT INTO `sign_logs` VALUES (236, 646561495, '2026-01-20 11:18:37', 6);
INSERT INTO `sign_logs` VALUES (237, 2051848341, '2026-01-20 11:33:25', 4);
INSERT INTO `sign_logs` VALUES (238, 508288539, '2026-01-20 13:49:26', 4);
INSERT INTO `sign_logs` VALUES (239, 761935676, '2026-01-20 15:03:17', 6);
INSERT INTO `sign_logs` VALUES (240, 7698928816, '2026-01-21 00:01:01', 10);
INSERT INTO `sign_logs` VALUES (241, 924854603, '2026-01-21 00:07:03', 9);
INSERT INTO `sign_logs` VALUES (242, 797391680, '2026-01-21 00:12:34', 5);
INSERT INTO `sign_logs` VALUES (243, 5514301656, '2026-01-21 00:24:39', 7);
INSERT INTO `sign_logs` VALUES (244, 1829581222, '2026-01-21 00:30:38', 10);
INSERT INTO `sign_logs` VALUES (245, 646561495, '2026-01-21 00:56:26', 5);
INSERT INTO `sign_logs` VALUES (246, 871229790, '2026-01-21 01:19:37', 4);
INSERT INTO `sign_logs` VALUES (247, 7550580807, '2026-01-21 01:23:04', 10);
INSERT INTO `sign_logs` VALUES (248, 1320890571, '2026-01-21 01:32:13', 6);
INSERT INTO `sign_logs` VALUES (249, 8061873913, '2026-01-21 07:10:09', 5);
INSERT INTO `sign_logs` VALUES (250, 8411082012, '2026-01-21 08:12:09', 10);
INSERT INTO `sign_logs` VALUES (251, 5234068298, '2026-01-21 08:15:39', 6);
INSERT INTO `sign_logs` VALUES (252, 761935676, '2026-01-21 08:21:21', 5);
INSERT INTO `sign_logs` VALUES (253, 7896336520, '2026-01-21 09:02:31', 9);
INSERT INTO `sign_logs` VALUES (254, 1316336246, '2026-01-21 12:39:33', 9);
INSERT INTO `sign_logs` VALUES (255, 2051848341, '2026-01-21 21:59:01', 7);
INSERT INTO `sign_logs` VALUES (256, 7640872861, '2026-01-21 22:32:47', 7);
INSERT INTO `sign_logs` VALUES (257, 7698928816, '2026-01-22 00:01:01', 8);
INSERT INTO `sign_logs` VALUES (258, 5514301656, '2026-01-22 00:10:28', 8);
INSERT INTO `sign_logs` VALUES (259, 924854603, '2026-01-22 00:34:06', 6);
INSERT INTO `sign_logs` VALUES (260, 1829581222, '2026-01-22 00:40:47', 8);
INSERT INTO `sign_logs` VALUES (261, 1316336246, '2026-01-22 00:42:55', 9);
INSERT INTO `sign_logs` VALUES (262, 797391680, '2026-01-22 07:31:53', 8);
INSERT INTO `sign_logs` VALUES (263, 761935676, '2026-01-22 08:12:57', 4);
INSERT INTO `sign_logs` VALUES (264, 8061873913, '2026-01-22 08:35:33', 8);
INSERT INTO `sign_logs` VALUES (265, 8411082012, '2026-01-22 09:10:11', 10);
INSERT INTO `sign_logs` VALUES (266, 7896336520, '2026-01-22 10:00:29', 5);
INSERT INTO `sign_logs` VALUES (267, 646561495, '2026-01-22 10:16:15', 7);
INSERT INTO `sign_logs` VALUES (268, 1320890571, '2026-01-22 12:16:39', 5);
INSERT INTO `sign_logs` VALUES (269, 7550580807, '2026-01-22 12:42:58', 8);
INSERT INTO `sign_logs` VALUES (270, 2051848341, '2026-01-22 13:01:05', 8);
INSERT INTO `sign_logs` VALUES (271, 6914122934, '2026-01-22 16:11:45', 7);
INSERT INTO `sign_logs` VALUES (272, 7640872861, '2026-01-22 17:42:03', 9);
INSERT INTO `sign_logs` VALUES (273, 7698928816, '2026-01-23 00:01:01', 7);
INSERT INTO `sign_logs` VALUES (274, 5514301656, '2026-01-23 00:01:35', 9);
INSERT INTO `sign_logs` VALUES (275, 1316336246, '2026-01-23 00:07:50', 7);
INSERT INTO `sign_logs` VALUES (276, 797391680, '2026-01-23 00:11:29', 7);
INSERT INTO `sign_logs` VALUES (277, 1829581222, '2026-01-23 00:37:04', 8);
INSERT INTO `sign_logs` VALUES (278, 761935676, '2026-01-23 00:39:43', 9);
INSERT INTO `sign_logs` VALUES (279, 646561495, '2026-01-23 01:54:09', 10);
INSERT INTO `sign_logs` VALUES (280, 7550580807, '2026-01-23 07:11:26', 10);
INSERT INTO `sign_logs` VALUES (281, 8411082012, '2026-01-23 07:35:56', 4);
INSERT INTO `sign_logs` VALUES (282, 7896336520, '2026-01-23 08:23:03', 9);
INSERT INTO `sign_logs` VALUES (283, 8061873913, '2026-01-23 09:17:54', 7);
INSERT INTO `sign_logs` VALUES (284, 508288539, '2026-01-23 13:37:01', 8);
INSERT INTO `sign_logs` VALUES (285, 6914122934, '2026-01-23 14:54:01', 7);
INSERT INTO `sign_logs` VALUES (286, 924854603, '2026-01-23 15:03:24', 8);
INSERT INTO `sign_logs` VALUES (287, 6977085303, '2026-01-23 15:07:43', 9);
INSERT INTO `sign_logs` VALUES (288, 1320890571, '2026-01-23 15:11:56', 6);
INSERT INTO `sign_logs` VALUES (289, 2051848341, '2026-01-23 17:20:40', 9);
INSERT INTO `sign_logs` VALUES (290, 5056439343, '2026-01-23 18:03:06', 5);
INSERT INTO `sign_logs` VALUES (291, 6902070388, '2026-01-23 18:08:24', 7);
INSERT INTO `sign_logs` VALUES (292, 8207259007, '2026-01-23 18:09:05', 6);
INSERT INTO `sign_logs` VALUES (293, 5081446599, '2026-01-23 18:09:41', 4);
INSERT INTO `sign_logs` VALUES (294, 7462224254, '2026-01-23 18:12:15', 4);
INSERT INTO `sign_logs` VALUES (295, 7640872861, '2026-01-23 21:03:26', 10);
INSERT INTO `sign_logs` VALUES (296, 8310966511, '2026-01-23 21:12:29', 6);
INSERT INTO `sign_logs` VALUES (297, 5514301656, '2026-01-24 00:00:25', 8);
INSERT INTO `sign_logs` VALUES (298, 7698928816, '2026-01-24 00:01:01', 4);
INSERT INTO `sign_logs` VALUES (299, 5081446599, '2026-01-24 00:01:08', 4);
INSERT INTO `sign_logs` VALUES (300, 7640872861, '2026-01-24 00:03:14', 8);
INSERT INTO `sign_logs` VALUES (301, 797391680, '2026-01-24 00:06:35', 9);
INSERT INTO `sign_logs` VALUES (302, 1316336246, '2026-01-24 00:09:36', 9);
INSERT INTO `sign_logs` VALUES (303, 7462224254, '2026-01-24 00:14:19', 7);
INSERT INTO `sign_logs` VALUES (304, 646561495, '2026-01-24 00:30:08', 4);
INSERT INTO `sign_logs` VALUES (305, 1829581222, '2026-01-24 00:42:51', 9);
INSERT INTO `sign_logs` VALUES (306, 8310966511, '2026-01-24 01:15:52', 4);
INSERT INTO `sign_logs` VALUES (307, 924854603, '2026-01-24 03:18:56', 7);
INSERT INTO `sign_logs` VALUES (308, 8411082012, '2026-01-24 06:54:39', 9);
INSERT INTO `sign_logs` VALUES (309, 2051848341, '2026-01-24 07:36:09', 9);
INSERT INTO `sign_logs` VALUES (310, 761935676, '2026-01-24 07:56:11', 6);
INSERT INTO `sign_logs` VALUES (311, 5234068298, '2026-01-24 09:24:16', 4);
INSERT INTO `sign_logs` VALUES (312, 8061873913, '2026-01-24 09:33:01', 5);
INSERT INTO `sign_logs` VALUES (313, 508288539, '2026-01-24 10:22:16', 4);
INSERT INTO `sign_logs` VALUES (314, 1320890571, '2026-01-24 12:00:08', 9);
INSERT INTO `sign_logs` VALUES (315, 7550580807, '2026-01-24 12:26:25', 9);
INSERT INTO `sign_logs` VALUES (316, 6914122934, '2026-01-24 15:22:32', 8);
INSERT INTO `sign_logs` VALUES (317, 8177623194, '2026-01-24 15:55:06', 5);
INSERT INTO `sign_logs` VALUES (318, 871229790, '2026-01-24 17:53:58', 10);
INSERT INTO `sign_logs` VALUES (319, 6322070620, '2026-01-24 21:48:13', 6);
INSERT INTO `sign_logs` VALUES (320, 6902070388, '2026-01-24 21:49:29', 8);
INSERT INTO `sign_logs` VALUES (321, 7288936301, '2026-01-24 22:00:23', 9);
INSERT INTO `sign_logs` VALUES (322, 797391680, '2026-01-25 00:00:48', 8);
INSERT INTO `sign_logs` VALUES (323, 7698928816, '2026-01-25 00:01:01', 5);
INSERT INTO `sign_logs` VALUES (324, 8310966511, '2026-01-25 00:04:17', 9);
INSERT INTO `sign_logs` VALUES (325, 5081446599, '2026-01-25 00:07:38', 10);
INSERT INTO `sign_logs` VALUES (326, 1829581222, '2026-01-25 00:08:57', 8);
INSERT INTO `sign_logs` VALUES (327, 5514301656, '2026-01-25 00:14:22', 8);
INSERT INTO `sign_logs` VALUES (328, 646561495, '2026-01-25 00:20:42', 5);
INSERT INTO `sign_logs` VALUES (329, 761935676, '2026-01-25 00:21:09', 6);
INSERT INTO `sign_logs` VALUES (330, 7462224254, '2026-01-25 01:40:13', 9);
INSERT INTO `sign_logs` VALUES (331, 1320890571, '2026-01-25 01:50:37', 4);
INSERT INTO `sign_logs` VALUES (332, 1316336246, '2026-01-25 02:58:45', 7);
INSERT INTO `sign_logs` VALUES (333, 8411082012, '2026-01-25 07:32:41', 9);
INSERT INTO `sign_logs` VALUES (334, 8177623194, '2026-01-25 07:42:02', 6);
INSERT INTO `sign_logs` VALUES (335, 5234068298, '2026-01-25 09:17:10', 5);
INSERT INTO `sign_logs` VALUES (336, 8061873913, '2026-01-25 10:31:14', 9);
INSERT INTO `sign_logs` VALUES (337, 924854603, '2026-01-25 12:00:40', 4);
INSERT INTO `sign_logs` VALUES (338, 7550580807, '2026-01-25 12:45:07', 10);
INSERT INTO `sign_logs` VALUES (339, 7896336520, '2026-01-25 14:01:17', 9);
INSERT INTO `sign_logs` VALUES (340, 6914122934, '2026-01-25 15:38:34', 8);
INSERT INTO `sign_logs` VALUES (341, 5056439343, '2026-01-25 20:45:56', 7);
INSERT INTO `sign_logs` VALUES (342, 5365747330, '2026-01-25 21:03:54', 10);
INSERT INTO `sign_logs` VALUES (343, 7640872861, '2026-01-25 23:07:50', 4);
INSERT INTO `sign_logs` VALUES (344, 7698928816, '2026-01-26 00:01:01', 4);
INSERT INTO `sign_logs` VALUES (345, 1316336246, '2026-01-26 00:05:11', 10);
INSERT INTO `sign_logs` VALUES (346, 7462224254, '2026-01-26 00:08:17', 10);
INSERT INTO `sign_logs` VALUES (347, 5365747330, '2026-01-26 00:10:11', 8);
INSERT INTO `sign_logs` VALUES (348, 5081446599, '2026-01-26 00:11:27', 9);
INSERT INTO `sign_logs` VALUES (349, 8310966511, '2026-01-26 00:13:53', 8);
INSERT INTO `sign_logs` VALUES (350, 5514301656, '2026-01-26 00:18:07', 9);
INSERT INTO `sign_logs` VALUES (351, 1829581222, '2026-01-26 00:34:49', 5);
INSERT INTO `sign_logs` VALUES (352, 8177623194, '2026-01-26 05:09:39', 8);
INSERT INTO `sign_logs` VALUES (353, 797391680, '2026-01-26 05:15:41', 4);
INSERT INTO `sign_logs` VALUES (354, 1320890571, '2026-01-26 05:30:51', 6);
INSERT INTO `sign_logs` VALUES (355, 8411082012, '2026-01-26 06:10:14', 10);
INSERT INTO `sign_logs` VALUES (356, 8061873913, '2026-01-26 07:10:18', 7);
INSERT INTO `sign_logs` VALUES (357, 646561495, '2026-01-26 07:49:16', 7);
INSERT INTO `sign_logs` VALUES (358, 761935676, '2026-01-26 07:52:34', 6);
INSERT INTO `sign_logs` VALUES (359, 924854603, '2026-01-26 08:04:58', 9);
INSERT INTO `sign_logs` VALUES (360, 6914122934, '2026-01-26 08:15:36', 5);
INSERT INTO `sign_logs` VALUES (361, 2051848341, '2026-01-26 08:30:11', 8);
INSERT INTO `sign_logs` VALUES (362, 5056439343, '2026-01-26 08:45:52', 10);
INSERT INTO `sign_logs` VALUES (363, 7896336520, '2026-01-26 09:59:37', 10);
INSERT INTO `sign_logs` VALUES (364, 6902070388, '2026-01-26 10:00:57', 10);
INSERT INTO `sign_logs` VALUES (365, 6977085303, '2026-01-26 10:01:17', 6);
INSERT INTO `sign_logs` VALUES (366, 6153524823, '2026-01-26 10:04:15', 4);
INSERT INTO `sign_logs` VALUES (367, 5234068298, '2026-01-26 11:38:06', 6);
INSERT INTO `sign_logs` VALUES (368, 7550580807, '2026-01-26 12:42:53', 6);
INSERT INTO `sign_logs` VALUES (369, 508288539, '2026-01-26 13:18:18', 8);
INSERT INTO `sign_logs` VALUES (370, 7640872861, '2026-01-26 21:27:35', 5);
INSERT INTO `sign_logs` VALUES (371, 7698928816, '2026-01-27 00:01:01', 10);
INSERT INTO `sign_logs` VALUES (372, 5514301656, '2026-01-27 00:03:51', 5);
INSERT INTO `sign_logs` VALUES (373, 8310966511, '2026-01-27 00:10:53', 8);
INSERT INTO `sign_logs` VALUES (374, 646561495, '2026-01-27 00:13:39', 6);
INSERT INTO `sign_logs` VALUES (375, 5081446599, '2026-01-27 00:14:10', 7);
INSERT INTO `sign_logs` VALUES (376, 1829581222, '2026-01-27 00:14:21', 4);
INSERT INTO `sign_logs` VALUES (377, 7462224254, '2026-01-27 00:18:38', 5);
INSERT INTO `sign_logs` VALUES (378, 761935676, '2026-01-27 00:21:05', 10);
INSERT INTO `sign_logs` VALUES (379, 1316336246, '2026-01-27 00:53:05', 10);
INSERT INTO `sign_logs` VALUES (380, 797391680, '2026-01-27 01:55:17', 7);
INSERT INTO `sign_logs` VALUES (381, 8411082012, '2026-01-27 06:22:50', 5);
INSERT INTO `sign_logs` VALUES (382, 6153524823, '2026-01-27 07:24:48', 7);
INSERT INTO `sign_logs` VALUES (383, 8061873913, '2026-01-27 07:34:50', 6);
INSERT INTO `sign_logs` VALUES (384, 8177623194, '2026-01-27 07:36:28', 4);
INSERT INTO `sign_logs` VALUES (385, 5234068298, '2026-01-27 08:13:48', 5);
INSERT INTO `sign_logs` VALUES (386, 7550580807, '2026-01-27 08:47:46', 4);
INSERT INTO `sign_logs` VALUES (387, 1320890571, '2026-01-27 09:22:30', 10);
INSERT INTO `sign_logs` VALUES (388, 924854603, '2026-01-27 09:54:39', 5);
INSERT INTO `sign_logs` VALUES (389, 5365747330, '2026-01-27 10:29:36', 9);
INSERT INTO `sign_logs` VALUES (390, 6914122934, '2026-01-27 16:51:46', 8);
INSERT INTO `sign_logs` VALUES (391, 2051848341, '2026-01-27 16:54:07', 10);
INSERT INTO `sign_logs` VALUES (392, 6524442943, '2026-01-27 17:50:44', 5);
INSERT INTO `sign_logs` VALUES (393, 6977085303, '2026-01-27 17:51:29', 8);
INSERT INTO `sign_logs` VALUES (394, 7788773392, '2026-01-27 17:52:48', 4);
INSERT INTO `sign_logs` VALUES (395, 1097156099, '2026-01-27 17:53:43', 7);
INSERT INTO `sign_logs` VALUES (396, 5738452450, '2026-01-27 17:54:02', 8);
INSERT INTO `sign_logs` VALUES (397, 5499341284, '2026-01-27 17:56:47', 4);
INSERT INTO `sign_logs` VALUES (398, 5825064778, '2026-01-27 18:00:44', 8);
INSERT INTO `sign_logs` VALUES (399, 1997397858, '2026-01-27 18:06:22', 6);
INSERT INTO `sign_logs` VALUES (400, 6410320989, '2026-01-27 18:08:20', 7);
INSERT INTO `sign_logs` VALUES (401, 7769118684, '2026-01-27 18:13:01', 6);
INSERT INTO `sign_logs` VALUES (402, 7228906298, '2026-01-27 18:24:32', 9);
INSERT INTO `sign_logs` VALUES (403, 877952308, '2026-01-27 18:25:58', 6);
INSERT INTO `sign_logs` VALUES (404, 8076379209, '2026-01-27 18:29:55', 7);
INSERT INTO `sign_logs` VALUES (405, 8133730697, '2026-01-27 18:31:08', 7);
INSERT INTO `sign_logs` VALUES (406, 7716072414, '2026-01-27 19:14:00', 10);
INSERT INTO `sign_logs` VALUES (407, 5056439343, '2026-01-27 19:19:52', 10);
INSERT INTO `sign_logs` VALUES (408, 6335704802, '2026-01-27 20:20:34', 7);
INSERT INTO `sign_logs` VALUES (409, 508288539, '2026-01-27 20:32:57', 6);
INSERT INTO `sign_logs` VALUES (410, 6902070388, '2026-01-27 20:48:21', 6);
INSERT INTO `sign_logs` VALUES (411, 5829761274, '2026-01-27 20:54:00', 5);
INSERT INTO `sign_logs` VALUES (412, 7896336520, '2026-01-27 21:25:32', 8);
INSERT INTO `sign_logs` VALUES (413, 871229790, '2026-01-27 21:29:32', 9);
INSERT INTO `sign_logs` VALUES (414, 1900924174, '2026-01-27 21:32:32', 9);
INSERT INTO `sign_logs` VALUES (415, 5445392415, '2026-01-27 22:02:01', 7);
INSERT INTO `sign_logs` VALUES (416, 7787907631, '2026-01-27 22:03:56', 8);
INSERT INTO `sign_logs` VALUES (417, 7702451111, '2026-01-27 22:09:01', 8);
INSERT INTO `sign_logs` VALUES (418, 7738604478, '2026-01-27 22:11:11', 5);
INSERT INTO `sign_logs` VALUES (419, 5605423655, '2026-01-27 22:48:05', 10);
INSERT INTO `sign_logs` VALUES (420, 5561606792, '2026-01-27 23:05:57', 7);
INSERT INTO `sign_logs` VALUES (421, 6543248350, '2026-01-27 23:07:02', 6);
INSERT INTO `sign_logs` VALUES (422, 598777718, '2026-01-27 23:07:50', 9);
INSERT INTO `sign_logs` VALUES (423, 7615101989, '2026-01-27 23:22:41', 10);
INSERT INTO `sign_logs` VALUES (424, 8351238042, '2026-01-27 23:27:35', 5);
INSERT INTO `sign_logs` VALUES (425, 7698928816, '2026-01-28 00:01:01', 7);
INSERT INTO `sign_logs` VALUES (426, 1316336246, '2026-01-28 00:03:16', 4);
INSERT INTO `sign_logs` VALUES (427, 5829761274, '2026-01-28 00:04:33', 4);
INSERT INTO `sign_logs` VALUES (428, 5499341284, '2026-01-28 00:06:36', 8);
INSERT INTO `sign_logs` VALUES (429, 7640872861, '2026-01-28 00:07:59', 5);
INSERT INTO `sign_logs` VALUES (430, 5081446599, '2026-01-28 00:08:17', 7);
INSERT INTO `sign_logs` VALUES (431, 5365747330, '2026-01-28 00:08:31', 9);
INSERT INTO `sign_logs` VALUES (432, 1997397858, '2026-01-28 00:08:43', 10);
INSERT INTO `sign_logs` VALUES (433, 7462224254, '2026-01-28 00:09:23', 5);
INSERT INTO `sign_logs` VALUES (434, 7228906298, '2026-01-28 00:15:42', 6);
INSERT INTO `sign_logs` VALUES (435, 1097156099, '2026-01-28 00:24:10', 5);
INSERT INTO `sign_logs` VALUES (436, 5561606792, '2026-01-28 00:49:21', 5);
INSERT INTO `sign_logs` VALUES (437, 646561495, '2026-01-28 00:52:05', 9);
INSERT INTO `sign_logs` VALUES (438, 5605423655, '2026-01-28 00:54:47', 4);
INSERT INTO `sign_logs` VALUES (439, 1829581222, '2026-01-28 01:04:20', 7);
INSERT INTO `sign_logs` VALUES (440, 5514301656, '2026-01-28 01:13:36', 4);
INSERT INTO `sign_logs` VALUES (441, 797391680, '2026-01-28 02:41:11', 4);
INSERT INTO `sign_logs` VALUES (442, 598777718, '2026-01-28 03:31:06', 5);
INSERT INTO `sign_logs` VALUES (443, 8177623194, '2026-01-28 04:58:45', 10);
INSERT INTO `sign_logs` VALUES (444, 642429037, '2026-01-28 05:34:17', 7);
INSERT INTO `sign_logs` VALUES (445, 8411082012, '2026-01-28 06:19:45', 9);
INSERT INTO `sign_logs` VALUES (446, 5738452450, '2026-01-28 06:55:34', 5);
INSERT INTO `sign_logs` VALUES (447, 5445392415, '2026-01-28 07:02:21', 9);
INSERT INTO `sign_logs` VALUES (448, 6153524823, '2026-01-28 07:30:49', 10);
INSERT INTO `sign_logs` VALUES (449, 2051848341, '2026-01-28 07:38:11', 5);
INSERT INTO `sign_logs` VALUES (450, 877952308, '2026-01-28 07:43:31', 6);
INSERT INTO `sign_logs` VALUES (451, 5234068298, '2026-01-28 08:17:33', 9);
INSERT INTO `sign_logs` VALUES (452, 6410320989, '2026-01-28 08:20:08', 10);
INSERT INTO `sign_logs` VALUES (453, 7788773392, '2026-01-28 08:21:09', 5);
INSERT INTO `sign_logs` VALUES (454, 1900924174, '2026-01-28 08:23:20', 4);
INSERT INTO `sign_logs` VALUES (455, 8061873913, '2026-01-28 08:23:55', 7);
INSERT INTO `sign_logs` VALUES (456, 7550580807, '2026-01-28 08:24:17', 10);
INSERT INTO `sign_logs` VALUES (457, 6524442943, '2026-01-28 08:31:19', 4);
INSERT INTO `sign_logs` VALUES (458, 7738604478, '2026-01-28 08:40:22', 8);
INSERT INTO `sign_logs` VALUES (459, 6335704802, '2026-01-28 08:40:26', 4);
INSERT INTO `sign_logs` VALUES (460, 7896336520, '2026-01-28 08:43:29', 8);
INSERT INTO `sign_logs` VALUES (461, 5848164110, '2026-01-28 08:46:10', 10);
INSERT INTO `sign_logs` VALUES (462, 7702451111, '2026-01-28 08:49:31', 7);
INSERT INTO `sign_logs` VALUES (463, 5825064778, '2026-01-28 09:04:26', 9);
INSERT INTO `sign_logs` VALUES (464, 8076379209, '2026-01-28 09:04:44', 7);
INSERT INTO `sign_logs` VALUES (465, 8133730697, '2026-01-28 09:04:54', 10);
INSERT INTO `sign_logs` VALUES (466, 6543248350, '2026-01-28 09:17:47', 9);
INSERT INTO `sign_logs` VALUES (467, 723293659, '2026-01-28 09:26:51', 5);
INSERT INTO `sign_logs` VALUES (468, 8310966511, '2026-01-28 09:29:24', 6);
INSERT INTO `sign_logs` VALUES (469, 599087014, '2026-01-28 09:31:51', 8);
INSERT INTO `sign_logs` VALUES (470, 6902070388, '2026-01-28 09:46:52', 5);
INSERT INTO `sign_logs` VALUES (471, 577763005, '2026-01-28 10:51:07', 7);
INSERT INTO `sign_logs` VALUES (472, 1320890571, '2026-01-28 10:58:35', 4);
INSERT INTO `sign_logs` VALUES (473, 6158593974, '2026-01-28 12:00:24', 10);
INSERT INTO `sign_logs` VALUES (474, 7615101989, '2026-01-28 12:02:38', 9);
INSERT INTO `sign_logs` VALUES (475, 7769118684, '2026-01-28 12:38:58', 7);
INSERT INTO `sign_logs` VALUES (476, 7716072414, '2026-01-28 12:39:10', 6);
INSERT INTO `sign_logs` VALUES (477, 508288539, '2026-01-28 12:50:33', 9);
INSERT INTO `sign_logs` VALUES (478, 311123171, '2026-01-28 13:04:47', 5);
INSERT INTO `sign_logs` VALUES (479, 6914122934, '2026-01-28 13:45:27', 7);
INSERT INTO `sign_logs` VALUES (480, 7787907631, '2026-01-28 13:58:57', 4);
INSERT INTO `sign_logs` VALUES (481, 5318030142, '2026-01-28 14:20:12', 4);
INSERT INTO `sign_logs` VALUES (482, 5909749985, '2026-01-28 14:57:10', 9);
INSERT INTO `sign_logs` VALUES (483, 1112501837, '2026-01-28 15:16:15', 8);
INSERT INTO `sign_logs` VALUES (484, 1001862438, '2026-01-28 15:18:16', 10);
INSERT INTO `sign_logs` VALUES (485, 6977085303, '2026-01-28 15:18:23', 9);
INSERT INTO `sign_logs` VALUES (486, 8355098134, '2026-01-28 15:35:01', 7);
INSERT INTO `sign_logs` VALUES (487, 8435978384, '2026-01-28 16:03:00', 9);
INSERT INTO `sign_logs` VALUES (488, 7288936301, '2026-01-28 16:10:34', 10);
INSERT INTO `sign_logs` VALUES (489, 761935676, '2026-01-28 16:12:03', 6);
INSERT INTO `sign_logs` VALUES (490, 8278611194, '2026-01-28 17:45:29', 8);
INSERT INTO `sign_logs` VALUES (491, 7681664034, '2026-01-28 17:47:08', 9);
INSERT INTO `sign_logs` VALUES (492, 7185332548, '2026-01-28 18:12:33', 4);
INSERT INTO `sign_logs` VALUES (493, 7837269980, '2026-01-28 18:28:08', 8);
INSERT INTO `sign_logs` VALUES (494, 8480863382, '2026-01-28 19:26:54', 10);
INSERT INTO `sign_logs` VALUES (495, 6975394604, '2026-01-28 20:38:49', 5);
INSERT INTO `sign_logs` VALUES (496, 5078487615, '2026-01-28 20:46:28', 7);
INSERT INTO `sign_logs` VALUES (497, 5056439343, '2026-01-28 20:52:25', 7);
INSERT INTO `sign_logs` VALUES (498, 7183459615, '2026-01-28 21:01:26', 6);
INSERT INTO `sign_logs` VALUES (499, 8342272112, '2026-01-28 21:13:50', 7);
INSERT INTO `sign_logs` VALUES (500, 5923317335, '2026-01-28 22:32:29', 10);
INSERT INTO `sign_logs` VALUES (501, 6474547919, '2026-01-28 22:44:39', 4);
INSERT INTO `sign_logs` VALUES (502, 5428609984, '2026-01-28 22:49:17', 6);
INSERT INTO `sign_logs` VALUES (503, 7528274944, '2026-01-28 22:58:11', 4);
INSERT INTO `sign_logs` VALUES (504, 1479870507, '2026-01-28 23:02:27', 6);
INSERT INTO `sign_logs` VALUES (505, 7625563036, '2026-01-28 23:54:36', 4);
INSERT INTO `sign_logs` VALUES (506, 877952308, '2026-01-29 00:00:16', 5);
INSERT INTO `sign_logs` VALUES (507, 6474547919, '2026-01-29 00:00:49', 6);
INSERT INTO `sign_logs` VALUES (508, 7698928816, '2026-01-29 00:01:01', 4);
INSERT INTO `sign_logs` VALUES (509, 5428609984, '2026-01-29 00:03:47', 9);
INSERT INTO `sign_logs` VALUES (510, 7681664034, '2026-01-29 00:04:50', 5);
INSERT INTO `sign_logs` VALUES (511, 1097156099, '2026-01-29 00:05:28', 4);
INSERT INTO `sign_logs` VALUES (512, 6335704802, '2026-01-29 00:07:25', 7);
INSERT INTO `sign_logs` VALUES (513, 5909749985, '2026-01-29 00:07:43', 8);
INSERT INTO `sign_logs` VALUES (514, 1829581222, '2026-01-29 00:07:57', 4);
INSERT INTO `sign_logs` VALUES (515, 7837269980, '2026-01-29 00:08:54', 4);
INSERT INTO `sign_logs` VALUES (516, 5514301656, '2026-01-29 00:16:38', 4);
INSERT INTO `sign_logs` VALUES (517, 8310966511, '2026-01-29 00:18:46', 8);
INSERT INTO `sign_logs` VALUES (518, 6543248350, '2026-01-29 00:31:10', 6);
INSERT INTO `sign_logs` VALUES (519, 1479870507, '2026-01-29 00:34:59', 6);
INSERT INTO `sign_logs` VALUES (520, 871229790, '2026-01-29 00:38:23', 8);
INSERT INTO `sign_logs` VALUES (521, 5365747330, '2026-01-29 00:59:19', 7);
INSERT INTO `sign_logs` VALUES (522, 7462224254, '2026-01-29 01:08:53', 8);
INSERT INTO `sign_logs` VALUES (523, 646561495, '2026-01-29 01:15:23', 7);
INSERT INTO `sign_logs` VALUES (524, 1316336246, '2026-01-29 01:25:24', 6);
INSERT INTO `sign_logs` VALUES (525, 1900924174, '2026-01-29 01:31:42', 7);
INSERT INTO `sign_logs` VALUES (526, 6158593974, '2026-01-29 01:34:19', 4);
INSERT INTO `sign_logs` VALUES (527, 598777718, '2026-01-29 01:44:56', 7);
INSERT INTO `sign_logs` VALUES (528, 577763005, '2026-01-29 01:49:59', 8);
INSERT INTO `sign_logs` VALUES (529, 5605423655, '2026-01-29 02:28:39', 6);
INSERT INTO `sign_logs` VALUES (530, 8355098134, '2026-01-29 03:39:22', 4);
INSERT INTO `sign_logs` VALUES (531, 5081446599, '2026-01-29 04:25:54', 10);
INSERT INTO `sign_logs` VALUES (532, 797391680, '2026-01-29 05:02:03', 4);
INSERT INTO `sign_logs` VALUES (533, 8177623194, '2026-01-29 05:30:32', 10);
INSERT INTO `sign_logs` VALUES (534, 7625563036, '2026-01-29 06:47:23', 4);
INSERT INTO `sign_logs` VALUES (535, 2051848341, '2026-01-29 06:51:24', 8);
INSERT INTO `sign_logs` VALUES (536, 6153524823, '2026-01-29 06:55:26', 7);
INSERT INTO `sign_logs` VALUES (537, 5923317335, '2026-01-29 06:55:34', 10);
INSERT INTO `sign_logs` VALUES (538, 7185332548, '2026-01-29 06:55:43', 6);
INSERT INTO `sign_logs` VALUES (539, 311123171, '2026-01-29 06:59:34', 9);
INSERT INTO `sign_logs` VALUES (540, 7183459615, '2026-01-29 07:16:38', 6);
INSERT INTO `sign_logs` VALUES (541, 642429037, '2026-01-29 07:17:14', 9);
INSERT INTO `sign_logs` VALUES (542, 7528274944, '2026-01-29 07:21:51', 7);
INSERT INTO `sign_logs` VALUES (543, 6975394604, '2026-01-29 07:26:29', 6);
INSERT INTO `sign_logs` VALUES (544, 867238743, '2026-01-29 07:32:12', 6);
INSERT INTO `sign_logs` VALUES (545, 5561606792, '2026-01-29 07:34:44', 9);
INSERT INTO `sign_logs` VALUES (546, 8061873913, '2026-01-29 07:39:35', 8);
INSERT INTO `sign_logs` VALUES (547, 835073218, '2026-01-29 07:53:16', 7);
INSERT INTO `sign_logs` VALUES (548, 5848164110, '2026-01-29 07:54:14', 5);
INSERT INTO `sign_logs` VALUES (549, 6410320989, '2026-01-29 07:57:09', 6);
INSERT INTO `sign_logs` VALUES (550, 6693878747, '2026-01-29 08:02:29', 6);
INSERT INTO `sign_logs` VALUES (551, 6524442943, '2026-01-29 08:04:27', 7);
INSERT INTO `sign_logs` VALUES (552, 8435978384, '2026-01-29 08:06:31', 5);
INSERT INTO `sign_logs` VALUES (553, 5318030142, '2026-01-29 08:14:31', 7);
INSERT INTO `sign_logs` VALUES (554, 7550580807, '2026-01-29 08:16:00', 5);
INSERT INTO `sign_logs` VALUES (555, 5445392415, '2026-01-29 08:18:42', 8);
INSERT INTO `sign_logs` VALUES (556, 7788773392, '2026-01-29 08:20:13', 8);
INSERT INTO `sign_logs` VALUES (557, 7738604478, '2026-01-29 08:24:34', 6);
INSERT INTO `sign_logs` VALUES (558, 8480863382, '2026-01-29 08:26:52', 10);
INSERT INTO `sign_logs` VALUES (559, 5234068298, '2026-01-29 08:28:24', 10);
INSERT INTO `sign_logs` VALUES (560, 8411082012, '2026-01-29 08:33:15', 9);
INSERT INTO `sign_logs` VALUES (561, 7716072414, '2026-01-29 08:38:21', 6);
INSERT INTO `sign_logs` VALUES (562, 599087014, '2026-01-29 08:40:46', 7);
INSERT INTO `sign_logs` VALUES (563, 1320890571, '2026-01-29 09:03:08', 10);
INSERT INTO `sign_logs` VALUES (564, 7228906298, '2026-01-29 09:05:05', 10);
INSERT INTO `sign_logs` VALUES (565, 723293659, '2026-01-29 09:05:16', 7);
INSERT INTO `sign_logs` VALUES (566, 6290655761, '2026-01-29 09:29:01', 9);
INSERT INTO `sign_logs` VALUES (567, 761935676, '2026-01-29 09:37:26', 6);
INSERT INTO `sign_logs` VALUES (568, 7702451111, '2026-01-29 09:38:21', 5);
INSERT INTO `sign_logs` VALUES (569, 7787907631, '2026-01-29 09:39:33', 4);
INSERT INTO `sign_logs` VALUES (570, 5825064778, '2026-01-29 09:55:31', 8);
INSERT INTO `sign_logs` VALUES (571, 8076379209, '2026-01-29 09:55:38', 7);
INSERT INTO `sign_logs` VALUES (572, 8133730697, '2026-01-29 09:55:48', 10);
INSERT INTO `sign_logs` VALUES (573, 5829761274, '2026-01-29 10:11:47', 10);
INSERT INTO `sign_logs` VALUES (574, 7615101989, '2026-01-29 10:22:28', 8);
INSERT INTO `sign_logs` VALUES (575, 8234890251, '2026-01-29 10:54:40', 9);
INSERT INTO `sign_logs` VALUES (576, 1001862438, '2026-01-29 11:01:14', 9);
INSERT INTO `sign_logs` VALUES (577, 7288936301, '2026-01-29 11:09:48', 5);

-- ----------------------------
-- Table structure for user_discount_codes
-- ----------------------------
DROP TABLE IF EXISTS `user_discount_codes`;
CREATE TABLE `user_discount_codes`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `tg_id` bigint(20) NOT NULL,
  `option_id` int(11) NOT NULL,
  `code` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `whmcs_promo_id` int(11) NULL DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `expires_at` timestamp NOT NULL,
  `used` tinyint(1) NULL DEFAULT 0 COMMENT '0=未使用, 1=已使用',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_code`(`code`) USING BTREE,
  INDEX `idx_tg_id`(`tg_id`) USING BTREE,
  INDEX `option_id`(`option_id`) USING BTREE,
  CONSTRAINT `user_discount_codes_ibfk_1` FOREIGN KEY (`tg_id`) REFERENCES `users` (`tg_id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `user_discount_codes_ibfk_2` FOREIGN KEY (`option_id`) REFERENCES `exchange_options` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 21 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Records of user_discount_codes
-- ----------------------------

-- ----------------------------
-- Table structure for users
-- ----------------------------
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users`  (
  `tg_id` bigint(20) NOT NULL,
  `whmcs_client_id` int(11) NULL DEFAULT NULL,
  `email` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `points` int(11) NULL DEFAULT 0,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`tg_id`) USING BTREE,
  UNIQUE INDEX `uq_tg_id`(`tg_id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Records of users
-- ----------------------------
INSERT INTO `users` VALUES (311123171, 244, 'en-sem+ids@outlook.com', 14, '2026-01-28 13:04:25');
INSERT INTO `users` VALUES (508288539, 26, 'madlaxcb@gmail.com', 161, '2026-01-08 20:27:51');
INSERT INTO `users` VALUES (577763005, 434, 'back.bobcat.tean@mask.me', 15, '2026-01-28 10:50:48');
INSERT INTO `users` VALUES (598777718, 366, 'heisenberg0518@gmail.com', 21, '2026-01-27 23:07:42');
INSERT INTO `users` VALUES (599087014, 543, 'x29762906@163.com', 15, '2026-01-28 09:31:45');
INSERT INTO `users` VALUES (642429037, 395, 'carolannbudenfyb92@gmail.com', 16, '2026-01-28 05:34:06');
INSERT INTO `users` VALUES (646561495, 106, 'mmxlyo@gmail.com', 219, '2026-01-06 08:56:22');
INSERT INTO `users` VALUES (723293659, 582, 'ethel32699@gmail.com', 12, '2026-01-28 09:26:43');
INSERT INTO `users` VALUES (761935676, 117, 'zc@molady.cc.cd', 2, '2026-01-06 16:10:50');
INSERT INTO `users` VALUES (797391680, 115, 'evolveshell@gmail.com', 88, '2026-01-06 22:42:34');
INSERT INTO `users` VALUES (835073218, 251, 'locxjj@outlook.com', 7, '2026-01-29 07:51:31');
INSERT INTO `users` VALUES (867238743, 469, 'lsf@yumail.pp.ua', 6, '2026-01-29 07:32:00');
INSERT INTO `users` VALUES (871229790, 134, 'yilovesky520@gmail.com', 31, '2026-01-21 01:19:26');
INSERT INTO `users` VALUES (877952308, 144, 'abcambrian@qq.com', 17, '2026-01-27 18:25:52');
INSERT INTO `users` VALUES (924854603, 126, 'qawerty@gmail.com', 97, '2026-01-13 15:10:10');
INSERT INTO `users` VALUES (1001862438, 233, 'lzjz0609@gmail.com', 19, '2026-01-28 15:17:15');
INSERT INTO `users` VALUES (1097156099, 332, 'herongjunjj@foxmail.com', 16, '2026-01-27 17:53:36');
INSERT INTO `users` VALUES (1112501837, 367, '83370667@qq.com', 8, '2026-01-28 15:15:57');
INSERT INTO `users` VALUES (1316336246, 103, 'shinnpeanut@163.com', 216, '2026-01-06 01:01:47');
INSERT INTO `users` VALUES (1320890571, 136, 'fengshuyao920@gmail.com', 60, '2026-01-21 01:31:56');
INSERT INTO `users` VALUES (1479870507, 574, 'winboooc@gmail.com', 12, '2026-01-28 23:02:23');
INSERT INTO `users` VALUES (1794591642, 28, 'iiimao@126.com', 17, '2026-01-14 17:35:29');
INSERT INTO `users` VALUES (1829581222, 114, 'pdaxing536@gmail.com', 106, '2026-01-08 13:13:31');
INSERT INTO `users` VALUES (1900924174, 179, 'fee.atrocious792@yuanyoupush.com', 20, '2026-01-27 21:32:25');
INSERT INTO `users` VALUES (1997397858, 191, 'fcoe@qq.com', 16, '2026-01-27 18:06:00');
INSERT INTO `users` VALUES (2051848341, 110, '287775856@qq.com', 162, '2026-01-09 00:26:57');
INSERT INTO `users` VALUES (5056439343, 64, 'lezonkataoka677@gmail.com', 61, '2026-01-13 20:12:57');
INSERT INTO `users` VALUES (5078487615, 573, '3688082@gmail.com', 7, '2026-01-28 20:46:18');
INSERT INTO `users` VALUES (5081446599, 185, 'wznio@outlook.com', 51, '2026-01-23 18:09:33');
INSERT INTO `users` VALUES (5234068298, 138, 'gzzypyh@gmail.com', 45, '2026-01-21 08:15:23');
INSERT INTO `users` VALUES (5318030142, 548, 'lu5861301@gmail.com', 11, '2026-01-28 14:20:06');
INSERT INTO `users` VALUES (5319014516, 108, 'doctor7000@gmail.com', 70, '2026-01-06 05:17:35');
INSERT INTO `users` VALUES (5365747330, 562, 'id_2048@qq.com', 43, '2026-01-25 21:03:34');
INSERT INTO `users` VALUES (5426150478, 61, '131hhha@gmail.com', 66, '2026-01-08 16:14:54');
INSERT INTO `users` VALUES (5428609984, 248, 'grogen.mustang235@yyyx.uk', 15, '2026-01-28 22:49:11');
INSERT INTO `users` VALUES (5445392415, 201, 'gentlekingyx@gmail.com', 24, '2026-01-27 22:01:50');
INSERT INTO `users` VALUES (5499341284, 279, '13420525993zwj@gmail.com', 12, '2026-01-27 17:56:38');
INSERT INTO `users` VALUES (5514301656, 118, 'fcmg2333@gmail.com', 108, '2026-01-06 17:30:39');
INSERT INTO `users` VALUES (5561606792, 292, 'xufaxin1115@gmail.com', 21, '2026-01-27 23:05:30');
INSERT INTO `users` VALUES (5605423655, 154, 'zkyqsrt@yahoo.com', 20, '2026-01-27 22:47:51');
INSERT INTO `users` VALUES (5738452450, 499, 'ctfox9959@163.com', 13, '2026-01-27 17:53:59');
INSERT INTO `users` VALUES (5794322722, 77, 'zl777317@gmail.com', 73, '2025-12-26 08:22:16');
INSERT INTO `users` VALUES (5825064778, 237, '3491928829@qq.com', 25, '2026-01-27 18:00:16');
INSERT INTO `users` VALUES (5829761274, 358, '5yk76yc8@cock.li', 19, '2026-01-27 20:53:52');
INSERT INTO `users` VALUES (5848164110, 558, 'info@akn.pp.ua', 15, '2026-01-28 08:45:32');
INSERT INTO `users` VALUES (5909749985, 598, '2224312860@qq.com', 17, '2026-01-28 14:56:54');
INSERT INTO `users` VALUES (5923317335, 316, 'chenmocc@proton.me', 20, '2026-01-28 22:32:19');
INSERT INTO `users` VALUES (6153524823, 455, 'tulipyun@gmail.com', 28, '2026-01-26 10:03:43');
INSERT INTO `users` VALUES (6158593974, 494, '269368029@qq.com', 14, '2026-01-28 12:00:10');
INSERT INTO `users` VALUES (6290655761, 145, 'wenyuanzhang806@gmail.com', 9, '2026-01-29 09:26:00');
INSERT INTO `users` VALUES (6322070620, 7, 'hey.04138714@gmail.com', 10015, '2026-01-09 22:23:00');
INSERT INTO `users` VALUES (6335704802, 414, 'kevinewbe@gmail.com', 18, '2026-01-27 20:19:43');
INSERT INTO `users` VALUES (6410320989, 600, 'amazon.swipe288@passinbox.com', 23, '2026-01-27 18:08:14');
INSERT INTO `users` VALUES (6426888358, 645, 'a3235216387@gmail.com', 0, '2026-01-28 00:17:24');
INSERT INTO `users` VALUES (6474547919, 535, 'bm@o-uu.com', 10, '2026-01-28 22:44:25');
INSERT INTO `users` VALUES (6524442943, 140, 'j4fyfxqwn@mozmail.com', 16, '2026-01-27 17:50:40');
INSERT INTO `users` VALUES (6543248350, 189, 'feishimisi585@gmail.com', 21, '2026-01-27 23:06:44');
INSERT INTO `users` VALUES (6693878747, 423, 'cao8008@gmail.com', 6, '2026-01-29 08:02:15');
INSERT INTO `users` VALUES (6899168287, 121, '648394245@qq.com', 60, '2026-01-08 16:39:23');
INSERT INTO `users` VALUES (6902070388, 521, 'gomyouhi@gmail.com', 36, '2026-01-23 18:08:17');
INSERT INTO `users` VALUES (6914122934, 71, 'zhu.waiting@proton.me', 160, '2026-01-01 18:07:15');
INSERT INTO `users` VALUES (6975394604, 628, 'felix1998@gmail.com', 11, '2026-01-28 20:38:37');
INSERT INTO `users` VALUES (6977085303, 2, '3079980988@qq.com', 8960, '2025-12-30 02:22:09');
INSERT INTO `users` VALUES (7183459615, 336, 'zaiye603@gmail.com', 12, '2026-01-28 21:01:15');
INSERT INTO `users` VALUES (7185332548, 210, 'qq105621@gmail.com', 10, '2026-01-28 18:12:12');
INSERT INTO `users` VALUES (7228906298, 223, 'mr.frankjsw@gmail.com', 25, '2026-01-27 18:23:59');
INSERT INTO `users` VALUES (7288936301, 351, 'coolmanl@proton.me', 24, '2026-01-24 22:00:18');
INSERT INTO `users` VALUES (7462224254, 105, 'zhu.waiting@proton.me', 67, '2026-01-06 02:42:39');
INSERT INTO `users` VALUES (7528274944, 425, 'lanfengshe@gmail.com', 11, '2026-01-28 22:57:59');
INSERT INTO `users` VALUES (7550580807, 135, '2687315072@qq.com', 72, '2026-01-21 01:22:46');
INSERT INTO `users` VALUES (7615101989, 97, 'qfzf@proton.me', 104, '2026-01-04 11:10:57');
INSERT INTO `users` VALUES (7625563036, 388, 'xiaosu6661@2925.com', 8, '2026-01-28 23:54:28');
INSERT INTO `users` VALUES (7640872861, 123, 'x66367@gmail.com', 164, '2026-01-09 00:39:03');
INSERT INTO `users` VALUES (7681664034, 601, 'hhf306297907@gmail.com', 14, '2026-01-28 17:46:50');
INSERT INTO `users` VALUES (7698928816, 70, 'stormhost@deepnode.net', 180, '2026-01-08 10:52:23');
INSERT INTO `users` VALUES (7702451111, 199, 'yxking0801@proton.me', 20, '2026-01-27 22:08:57');
INSERT INTO `users` VALUES (7716072414, 590, 'dxhncs191223@gmail.com', 22, '2026-01-27 19:13:22');
INSERT INTO `users` VALUES (7738604478, 239, 'jaykingwx@proton.me', 19, '2026-01-27 22:11:06');
INSERT INTO `users` VALUES (7769118684, 396, 'hamsteryhz@gmail.com', 13, '2026-01-27 18:12:56');
INSERT INTO `users` VALUES (7787907631, 159, 'libob2418@gmail.com', 16, '2026-01-27 22:03:46');
INSERT INTO `users` VALUES (7788773392, 428, 'just201207@freesvip.eu.org', 17, '2026-01-27 17:52:30');
INSERT INTO `users` VALUES (7827117448, 43, 'linsh524@gmail.com', 106, '2026-01-08 10:50:05');
INSERT INTO `users` VALUES (7837269980, 502, 'soulmate@digita.qzz.io', 12, '2026-01-28 18:28:03');
INSERT INTO `users` VALUES (7896336520, 112, 'cao000407@gmail.com', 89, '2026-01-08 14:30:40');
INSERT INTO `users` VALUES (8061873913, 113, 'zterhk@yyyx.app', 94, '2026-01-14 11:45:23');
INSERT INTO `users` VALUES (8076379209, 196, 'bigyannick2@gmail.com', 21, '2026-01-27 18:29:50');
INSERT INTO `users` VALUES (8133730697, 217, '3137898600@qq.com', 27, '2026-01-27 18:31:03');
INSERT INTO `users` VALUES (8177623194, 368, 'pan277496444@gmail.com', 43, '2026-01-24 15:55:01');
INSERT INTO `users` VALUES (8207259007, 147, 'miyakedaxa603@gmail.com', 6, '2026-01-23 18:08:53');
INSERT INTO `users` VALUES (8234890251, 610, 'leoliuxinxin@gmail.com', 9, '2026-01-29 10:54:20');
INSERT INTO `users` VALUES (8278611194, 644, 'chisgmsinge@gmail.com', 8, '2026-01-28 17:45:22');
INSERT INTO `users` VALUES (8310966511, 589, 'hf1161635317@gmail.com', 49, '2026-01-23 21:12:20');
INSERT INTO `users` VALUES (8313016513, 1, 'nmslse@qq.com', 9999, '2026-01-01 01:31:24');
INSERT INTO `users` VALUES (8342272112, 563, '1224403167@qq.com', 7, '2026-01-28 21:07:49');
INSERT INTO `users` VALUES (8351238042, 220, 'xiangcheng1223@gmail.com', 5, '2026-01-27 23:26:57');
INSERT INTO `users` VALUES (8355098134, 595, 'xiaodudea@gmail.com', 11, '2026-01-28 15:34:39');
INSERT INTO `users` VALUES (8411082012, 139, 'qq353167950@gmail.com', 75, '2026-01-21 08:12:03');
INSERT INTO `users` VALUES (8435978384, 243, 'lsy66606@gmail.com', 14, '2026-01-28 16:02:36');
INSERT INTO `users` VALUES (8480863382, 539, '917661154@qq.com', 20, '2026-01-28 19:26:48');

-- ----------------------------
-- Table structure for verification_codes
-- ----------------------------
DROP TABLE IF EXISTS `verification_codes`;
CREATE TABLE `verification_codes`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `tg_id` bigint(20) NULL DEFAULT NULL,
  `email` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `code` varchar(6) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `expires_at` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `tg_id`(`tg_id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 152 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Records of verification_codes
-- ----------------------------

-- ----------------------------
-- Triggers structure for table prize_wins
-- ----------------------------
DROP TRIGGER IF EXISTS `bi_prize_wins_points`;
delimiter ;;
CREATE TRIGGER `bi_prize_wins_points` BEFORE INSERT ON `prize_wins` FOR EACH ROW BEGIN
  IF NEW.prize_type = 'points' AND NEW.auto_credit = 1 THEN
    SET NEW.status = 'fulfilled';
    IF NEW.fulfilled_at IS NULL THEN
      SET NEW.fulfilled_at = NOW(3);
    END IF;
  END IF;
END
;;
delimiter ;

-- ----------------------------
-- Triggers structure for table prize_wins
-- ----------------------------
DROP TRIGGER IF EXISTS `ai_prize_wins_points`;
delimiter ;;
CREATE TRIGGER `ai_prize_wins_points` AFTER INSERT ON `prize_wins` FOR EACH ROW BEGIN
  IF NEW.prize_type = 'points' AND NEW.auto_credit = 1 THEN
    UPDATE users
      SET points = points + IFNULL(NEW.points_amount, 0)
    WHERE tg_id = NEW.tg_id;
  END IF;
END
;;
delimiter ;

SET FOREIGN_KEY_CHECKS = 1;
