-- ============================================
-- CREATE DATABASE
-- ============================================
CREATE DATABASE IF NOT EXISTS EchoDB
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE EchoDB;

-- ============================================
-- TABLES (NO FOREIGN KEYS YET)
-- ============================================

CREATE TABLE IF NOT EXISTS Users (
    user_id CHAR(36) PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    bio TEXT,
    profile_media_id CHAR(36),
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at DATETIME NULL,
    deleted_by CHAR(36) NULL,
    is_banned BOOLEAN DEFAULT FALSE,
    banned_at DATETIME NULL,
    banned_by CHAR(36) NULL,
    ban_reason TEXT NULL,
    ban_expires_at DATETIME NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
) ENGINE=InnoDB;

CREATE INDEX idx_users_profile_media ON Users(profile_media_id);
CREATE INDEX idx_users_deleted_by ON Users(deleted_by);
CREATE INDEX idx_users_banned_by ON Users(banned_by);
CREATE INDEX idx_users_is_banned ON Users(is_banned);

-- ----------------------------------------------------------

CREATE TABLE IF NOT EXISTS Roles (
    role_id CHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
) ENGINE=InnoDB;

-- ----------------------------------------------------------

CREATE TABLE IF NOT EXISTS UserRoles (
    user_id CHAR(36),
    role_id CHAR(36),
    assigned_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    PRIMARY KEY (user_id, role_id)
) ENGINE=InnoDB;

CREATE INDEX idx_userroles_user ON UserRoles(user_id);
CREATE INDEX idx_userroles_role ON UserRoles(role_id);

-- ----------------------------------------------------------

CREATE TABLE IF NOT EXISTS BanHistory (
    ban_id CHAR(36) PRIMARY KEY,
    user_id CHAR(36) NOT NULL,
    moderator_id CHAR(36) NULL,
    reason TEXT,
    banned_at DATETIME NOT NULL,
    ban_expires_at DATETIME NULL,
    unbanned_at DATETIME NULL,
    unbanned_by CHAR(36) NULL
) ENGINE=InnoDB;

CREATE INDEX idx_banhistory_user ON BanHistory(user_id);
CREATE INDEX idx_banhistory_moderator ON BanHistory(moderator_id);

-- ----------------------------------------------------------

CREATE TABLE IF NOT EXISTS Posts (
    post_id CHAR(36) PRIMARY KEY,
    user_id CHAR(36) NOT NULL,
    content TEXT NOT NULL,
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at DATETIME NULL,
    deleted_by CHAR(36) NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
) ENGINE=InnoDB;

CREATE INDEX idx_posts_user ON Posts(user_id);
CREATE INDEX idx_posts_created_at ON Posts(created_at);
CREATE INDEX idx_posts_deleted_by ON Posts(deleted_by);

-- ----------------------------------------------------------

CREATE TABLE IF NOT EXISTS Replies (
    reply_id CHAR(36) PRIMARY KEY,
    parent_post_id CHAR(36) NULL,
    parent_reply_id CHAR(36) NULL,
    user_id CHAR(36) NOT NULL,
    content TEXT NOT NULL,
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at DATETIME NULL,
    deleted_by CHAR(36) NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
) ENGINE=InnoDB;

CREATE INDEX idx_replies_user ON Replies(user_id);
CREATE INDEX idx_replies_parent_post ON Replies(parent_post_id);
CREATE INDEX idx_replies_parent_reply ON Replies(parent_reply_id);
CREATE INDEX idx_replies_created_at ON Replies(created_at);

-- ----------------------------------------------------------

CREATE TABLE IF NOT EXISTS UserGroups (
    group_id CHAR(36) PRIMARY KEY,
    created_by CHAR(36) NOT NULL,
    origin_post_id CHAR(36) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at DATETIME NULL,
    deleted_by CHAR(36) NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
) ENGINE=InnoDB;

CREATE INDEX idx_usergroups_created_by ON UserGroups(created_by);
CREATE INDEX idx_usergroups_origin_post ON UserGroups(origin_post_id);
CREATE INDEX idx_usergroups_deleted_by ON UserGroups(deleted_by);

-- ----------------------------------------------------------

CREATE TABLE IF NOT EXISTS GroupMembers (
    group_id CHAR(36),
    user_id CHAR(36),
    joined_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    PRIMARY KEY (group_id, user_id)
) ENGINE=InnoDB;

CREATE INDEX idx_groupmembers_user ON GroupMembers(user_id);

-- ----------------------------------------------------------

CREATE TABLE IF NOT EXISTS ReactionTypes (
    reaction_type_id CHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
) ENGINE=InnoDB;

-- ----------------------------------------------------------

CREATE TABLE IF NOT EXISTS Reactions (
    reaction_id CHAR(36) PRIMARY KEY,
    user_id CHAR(36) NOT NULL,
    post_id CHAR(36) NULL,
    reply_id CHAR(36) NULL,
    reaction_type_id CHAR(36) NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
) ENGINE=InnoDB;

CREATE INDEX idx_reactions_user ON Reactions(user_id);
CREATE INDEX idx_reactions_post ON Reactions(post_id);
CREATE INDEX idx_reactions_reply ON Reactions(reply_id);
CREATE INDEX idx_reactions_type ON Reactions(reaction_type_id);

-- ----------------------------------------------------------

CREATE TABLE IF NOT EXISTS Reposts (
    repost_id CHAR(36) PRIMARY KEY,
    user_id CHAR(36) NOT NULL,
    post_id CHAR(36) NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
) ENGINE=InnoDB;

CREATE INDEX idx_reposts_user ON Reposts(user_id);
CREATE INDEX idx_reposts_post ON Reposts(post_id);

-- ----------------------------------------------------------

CREATE TABLE IF NOT EXISTS Followers (
    follower_id CHAR(36),
    followed_id CHAR(36),
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    PRIMARY KEY (follower_id, followed_id)
) ENGINE=InnoDB;

CREATE INDEX idx_followers_follower ON Followers(follower_id);
CREATE INDEX idx_followers_followed ON Followers(followed_id);

-- ----------------------------------------------------------

CREATE TABLE IF NOT EXISTS Media (
    media_id CHAR(36) PRIMARY KEY,
    post_id CHAR(36) NULL,
    reply_id CHAR(36) NULL,
    url VARCHAR(500) NOT NULL,
    media_type VARCHAR(50) NOT NULL,
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at DATETIME NULL,
    deleted_by CHAR(36) NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
) ENGINE=InnoDB;

CREATE INDEX idx_media_post ON Media(post_id);
CREATE INDEX idx_media_reply ON Media(reply_id);
CREATE INDEX idx_media_deleted_by ON Media(deleted_by);

-- ----------------------------------------------------------

CREATE TABLE IF NOT EXISTS ModerationActions (
    action_id CHAR(36) PRIMARY KEY,
    moderator_id CHAR(36) NULL,
    post_id CHAR(36) NULL,
    reply_id CHAR(36) NULL,
    user_id CHAR(36) NULL,
    action_type VARCHAR(255) NOT NULL,
    reason TEXT,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
) ENGINE=InnoDB;

CREATE INDEX idx_modactions_moderator ON ModerationActions(moderator_id);
CREATE INDEX idx_modactions_post ON ModerationActions(post_id);
CREATE INDEX idx_modactions_reply ON ModerationActions(reply_id);
CREATE INDEX idx_modactions_user ON ModerationActions(user_id);

-- ----------------------------------------------------------

CREATE TABLE IF NOT EXISTS Notifications (
    notification_id CHAR(36) PRIMARY KEY,
    user_id CHAR(36) NOT NULL,
    triggered_by_user_id CHAR(36) NULL,
    post_id CHAR(36) NULL,
    reply_id CHAR(36) NULL,
    type VARCHAR(255) NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
) ENGINE=InnoDB;

CREATE INDEX idx_notifications_user ON Notifications(user_id);
CREATE INDEX idx_notifications_triggered_by ON Notifications(triggered_by_user_id);
CREATE INDEX idx_notifications_post ON Notifications(post_id);
CREATE INDEX idx_notifications_reply ON Notifications(reply_id);
CREATE INDEX idx_notifications_is_read ON Notifications(is_read);

-- ----------------------------------------------------------

CREATE TABLE IF NOT EXISTS Mentions (
    mention_id CHAR(36) PRIMARY KEY,
    post_id CHAR(36) NULL,
    reply_id CHAR(36) NULL,
    mentioned_user_id CHAR(36) NOT NULL,
    created_at DATETIME NOT NULL
) ENGINE=InnoDB;

CREATE INDEX idx_mentions_post ON Mentions(post_id);
CREATE INDEX idx_mentions_reply ON Mentions(reply_id);
CREATE INDEX idx_mentions_user ON Mentions(mentioned_user_id);

-- ============================================
-- FOREIGN KEYS (ADDED AT THE END)
-- ============================================

ALTER TABLE Users
  ADD CONSTRAINT fk_users_profile_media FOREIGN KEY (profile_media_id) REFERENCES Media(media_id) ON DELETE SET NULL,
  ADD CONSTRAINT fk_users_deleted_by FOREIGN KEY (deleted_by) REFERENCES Users(user_id) ON DELETE SET NULL,
  ADD CONSTRAINT fk_users_banned_by FOREIGN KEY (banned_by) REFERENCES Users(user_id) ON DELETE SET NULL;

ALTER TABLE UserRoles
  ADD CONSTRAINT fk_userroles_user FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
  ADD CONSTRAINT fk_userroles_role FOREIGN KEY (role_id) REFERENCES Roles(role_id) ON DELETE CASCADE;

ALTER TABLE BanHistory
  ADD CONSTRAINT fk_banhistory_user FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
  ADD CONSTRAINT fk_banhistory_moderator FOREIGN KEY (moderator_id) REFERENCES Users(user_id) ON DELETE SET NULL,
  ADD CONSTRAINT fk_banhistory_unbanned_by FOREIGN KEY (unbanned_by) REFERENCES Users(user_id) ON DELETE SET NULL;

ALTER TABLE Posts
  ADD CONSTRAINT fk_posts_user FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
  ADD CONSTRAINT fk_posts_deleted_by FOREIGN KEY (deleted_by) REFERENCES Users(user_id) ON DELETE SET NULL;

ALTER TABLE Replies
  ADD CONSTRAINT fk_replies_user FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
  ADD CONSTRAINT fk_replies_parent_post FOREIGN KEY (parent_post_id) REFERENCES Posts(post_id) ON DELETE CASCADE,
  ADD CONSTRAINT fk_replies_parent_reply FOREIGN KEY (parent_reply_id) REFERENCES Replies(reply_id) ON DELETE CASCADE,
  ADD CONSTRAINT fk_replies_deleted_by FOREIGN KEY (deleted_by) REFERENCES Users(user_id) ON DELETE SET NULL;

ALTER TABLE UserGroups
  ADD CONSTRAINT fk_usergroups_creator FOREIGN KEY (created_by) REFERENCES Users(user_id) ON DELETE CASCADE,
  ADD CONSTRAINT fk_usergroups_origin_post FOREIGN KEY (origin_post_id) REFERENCES Posts(post_id) ON DELETE CASCADE,
  ADD CONSTRAINT fk_usergroups_deleted_by FOREIGN KEY (deleted_by) REFERENCES Users(user_id) ON DELETE SET NULL;

ALTER TABLE GroupMembers
  ADD CONSTRAINT fk_groupmembers_group FOREIGN KEY (group_id) REFERENCES UserGroups(group_id) ON DELETE CASCADE,
  ADD CONSTRAINT fk_groupmembers_user FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE;

ALTER TABLE Reactions
  ADD CONSTRAINT fk_reactions_user FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
  ADD CONSTRAINT fk_reactions_post FOREIGN KEY (post_id) REFERENCES Posts(post_id) ON DELETE CASCADE,
  ADD CONSTRAINT fk_reactions_reply FOREIGN KEY (reply_id) REFERENCES Replies(reply_id) ON DELETE CASCADE,
  ADD CONSTRAINT fk_reactions_type FOREIGN KEY (reaction_type_id) REFERENCES ReactionTypes(reaction_type_id) ON DELETE CASCADE;

ALTER TABLE Reposts
  ADD CONSTRAINT fk_reposts_user FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
  ADD CONSTRAINT fk_reposts_post FOREIGN KEY (post_id) REFERENCES Posts(post_id) ON DELETE CASCADE;

ALTER TABLE Followers
  ADD CONSTRAINT fk_followers_follower FOREIGN KEY (follower_id) REFERENCES Users(user_id) ON DELETE CASCADE,
  ADD CONSTRAINT fk_followers_followed FOREIGN KEY (followed_id) REFERENCES Users(user_id) ON DELETE CASCADE;

ALTER TABLE Media
  ADD CONSTRAINT fk_media_post FOREIGN KEY (post_id) REFERENCES Posts(post_id) ON DELETE CASCADE,
  ADD CONSTRAINT fk_media_reply FOREIGN KEY (reply_id) REFERENCES Replies(reply_id) ON DELETE CASCADE,
  ADD CONSTRAINT fk_media_deleted_by FOREIGN KEY (deleted_by) REFERENCES Users(user_id) ON DELETE SET NULL;

ALTER TABLE ModerationActions
  ADD CONSTRAINT fk_modactions_moderator FOREIGN KEY (moderator_id) REFERENCES Users(user_id) ON DELETE SET NULL,
  ADD CONSTRAINT fk_modactions_post FOREIGN KEY (post_id) REFERENCES Posts(post_id) ON DELETE CASCADE,
  ADD CONSTRAINT fk_modactions_reply FOREIGN KEY (reply_id) REFERENCES Replies(reply_id) ON DELETE CASCADE,
  ADD CONSTRAINT fk_modactions_user FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE SET NULL;

ALTER TABLE Notifications
  ADD CONSTRAINT fk_notifications_user FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
  ADD CONSTRAINT fk_notifications_triggered_by FOREIGN KEY (triggered_by_user_id) REFERENCES Users(user_id) ON DELETE SET NULL,
  ADD CONSTRAINT fk_notifications_post FOREIGN KEY (post_id) REFERENCES Posts(post_id) ON DELETE CASCADE,
  ADD CONSTRAINT fk_notifications_reply FOREIGN KEY (reply_id) REFERENCES Replies(reply_id) ON DELETE CASCADE;

ALTER TABLE Mentions
  ADD CONSTRAINT fk_mentions_post FOREIGN KEY (post_id) REFERENCES Posts(post_id) ON DELETE CASCADE,
  ADD CONSTRAINT fk_mentions_reply FOREIGN KEY (reply_id) REFERENCES Replies(reply_id) ON DELETE CASCADE,
  ADD CONSTRAINT fk_mentions_user FOREIGN KEY (mentioned_user_id) REFERENCES Users(user_id) ON DELETE CASCADE;
