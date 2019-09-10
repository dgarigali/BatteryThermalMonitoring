CREATE DATABASE `batt_temp_db`;

use batt_temp_db;

DROP TABLE IF EXISTS `downlink`;
DROP TABLE IF EXISTS `temp_sensor`;
DROP TABLE IF EXISTS `red_image`;
DROP TABLE IF EXISTS `image`;
DROP TABLE IF EXISTS `node`;

# Create and insert data into node table

CREATE TABLE `node` (
  `id` varchar(50) NOT NULL,
  `fan` varchar(10) NOT NULL, # on or off
  `mode` varchar(10) NOT NULL, # slow or fast
  `threshold` int NOT NULL,
  `temp_max` decimal(4,1) NOT NULL,
  PRIMARY KEY (`id`)
);
insert into `node`(`id`,`fan`,`mode`,`threshold`, `temp_max`) value ('node1','off','fast', 50, 300.0);

# Create and insert data into image table

CREATE TABLE `image` (
  `node_id` varchar(50) NOT NULL,
  `timestamp` DATETIME NOT NULL,
  `path` varchar(100) NOT NULL,
  `temp_max` decimal(4,1) NOT NULL,
  `temp_min` decimal(4,1) NOT NULL,
  PRIMARY KEY (`timestamp`),
  foreign key(node_id) references node(id)
);

# Create and insert data into red_image table

CREATE TABLE `red_image` (
  `node_id` varchar(50) NOT NULL,
  `timestamp` DATETIME NOT NULL,
  `path` varchar(100) NOT NULL,
  `temp_max` decimal(4,1) NOT NULL,
  `temp_min` decimal(4,1) NOT NULL,
  PRIMARY KEY (`timestamp`),
  foreign key(node_id) references node(id)
);

# Create and insert data into temp_sensor table

CREATE TABLE `temp_sensor` (
  `node_id` varchar(50) NOT NULL,
  `timestamp` DATETIME,
  `env_temp` int,
  PRIMARY KEY (`node_id`),
  foreign key(node_id) references node(id)
);
insert into `temp_sensor`(`node_id`) value ('node1');

# Create and insert data into downlink table

CREATE TABLE `downlink` (
  `node_id` varchar(50) NOT NULL,
  `flag` boolean NOT NULL,
  `counter` int NOT NULL,
  `fan` varchar(10), # on or off
  `mode` varchar(10), # slow or fast
  `threshold` int,
  PRIMARY KEY (`node_id`),
  foreign key(node_id) references node(id)
);
insert into `downlink`(`node_id`, `flag`, `counter`) value ('node1', false, 0);