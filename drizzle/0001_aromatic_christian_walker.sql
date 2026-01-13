CREATE TABLE `download_queue` (
	`id` int AUTO_INCREMENT NOT NULL,
	`userId` int NOT NULL,
	`youtubeUrl` text NOT NULL,
	`youtubeId` varchar(64) NOT NULL,
	`status` enum('pending','processing','completed','failed') NOT NULL DEFAULT 'pending',
	`errorMessage` text,
	`videoId` int,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `download_queue_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `telegram_sessions` (
	`id` int AUTO_INCREMENT NOT NULL,
	`authToken` varchar(64) NOT NULL,
	`telegramUserId` bigint,
	`telegramUsername` varchar(255),
	`userId` int,
	`verified` boolean NOT NULL DEFAULT false,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`expiresAt` timestamp NOT NULL,
	CONSTRAINT `telegram_sessions_id` PRIMARY KEY(`id`),
	CONSTRAINT `telegram_sessions_authToken_unique` UNIQUE(`authToken`)
);
--> statement-breakpoint
CREATE TABLE `videos` (
	`id` int AUTO_INCREMENT NOT NULL,
	`userId` int NOT NULL,
	`youtubeId` varchar(64) NOT NULL,
	`title` text NOT NULL,
	`description` text,
	`thumbnailUrl` text,
	`duration` int,
	`fileKey` text NOT NULL,
	`fileUrl` text NOT NULL,
	`fileSize` bigint,
	`mimeType` varchar(100),
	`status` enum('downloading','ready','failed') NOT NULL DEFAULT 'downloading',
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `videos_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
ALTER TABLE `download_queue` ADD CONSTRAINT `download_queue_userId_users_id_fk` FOREIGN KEY (`userId`) REFERENCES `users`(`id`) ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE `download_queue` ADD CONSTRAINT `download_queue_videoId_videos_id_fk` FOREIGN KEY (`videoId`) REFERENCES `videos`(`id`) ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE `telegram_sessions` ADD CONSTRAINT `telegram_sessions_userId_users_id_fk` FOREIGN KEY (`userId`) REFERENCES `users`(`id`) ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE `videos` ADD CONSTRAINT `videos_userId_users_id_fk` FOREIGN KEY (`userId`) REFERENCES `users`(`id`) ON DELETE no action ON UPDATE no action;