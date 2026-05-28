# Catalogue deployment

Resource: debian 12

## Suggested on Debian 12.13: Eclipse Temurin 25.

```shell script
sudo apt update
sudo apt install -y wget apt-transport-https gpg lsb-release
wget -qO - https://packages.adoptium.net/artifactory/api/gpg/key/public \
  | gpg --dearmor \
  | sudo tee /usr/share/keyrings/adoptium.gpg > /dev/null

echo "deb [signed-by=/usr/share/keyrings/adoptium.gpg] https://packages.adoptium.net/artifactory/deb $(lsb_release -cs) main" \
  | sudo tee /etc/apt/sources.list.d/adoptium.list

sudo apt update
sudo apt install -y temurin-25-jdk
```

## Verify

```shell script
$ java -version 
openjdk version "25.0.3" 2026-04-21 LTS 
OpenJDK Runtime Environment Temurin-25.0.3+9 (build 25.0.3+9-LTS) 
OpenJDK 64-Bit Server VM Temurin-25.0.3+9 (build 25.0.3+9-LTS, mixed mode, sharing)
$ javac -version 
javac 25.0.3 
$ mvn -version 
Apache Maven 3.8.7 
Maven home: /usr/share/maven 
Java version: 25.0.3, vendor: Eclipse Adoptium, runtime: /usr/lib/jvm/temurin-25-jdk-amd64 
Default locale: en, platform encoding: UTF-8 OS 
name: "linux", version: "6.1.0-43-amd64", arch: "amd64", family: "unix"
```

## Install/run MariaDB

```shell script
sudo apt install mariadb-server
sudo systemctl enable --now mariadb
```

## Create DB

```shell script
sudo mariadb
CREATE DATABASE eoscnode CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'eoscnode'@'localhost' IDENTIFIED BY 'password_sicura';
GRANT ALL PRIVILEGES ON eoscnode.* TO 'eoscnode'@'localhost';
FLUSH PRIVILEGES;
```

## Create tables not managed by Hibernate: br_eoscdata_purpose, br_eoscdata_customer_segment, br_eoscdata_end_user_groups

```shell script
use eoscnode

CREATE TABLE IF NOT EXISTS br_eoscdata_purpose (
  palvelu INT NOT NULL,
  purpose INT NOT NULL,
  PRIMARY KEY (palvelu, purpose)
);

CREATE TABLE IF NOT EXISTS br_eoscdata_customer_segment (
  id INT NOT NULL,
  cs_id INT NOT NULL,
  PRIMARY KEY (id, cs_id)
);

CREATE TABLE IF NOT EXISTS br_eoscdata_end_user_groups (
  id INT NOT NULL,
  eug_id INT NOT NULL,
  PRIMARY KEY (id, eug_id)
);
```

## Configure src/main/resources/application.properties

```shell script
quarkus.datasource.db-kind=mariadb
quarkus.datasource.username=eoscnode
quarkus.datasource.password=password_sicura
quarkus.datasource.jdbc.url=jdbc:mariadb://localhost:3306/eoscnode
quarkus.hibernate-orm.database.generation=drop-and-create  -- first run, with empty DB
quarkus.hibernate-orm.database.generation=validate -- after first run
```

## Start Quarkus binded on all interfaces

```shell script
MAVEN_OPTS="--add-opens java.base/java.lang=ALL-UNNAMED" mvn compile quarkus:dev -Dquarkus.http.host=0.0.0.0
```

## Endpoints API:
```shell script
/v1/service
/v1/nodes
/v1/purposes
/v1/accesstypes
/v1/customersegments
/v1/endusers
```

## Swagger UI :
http://IP_DEL_SERVER:8080/q/swagger-ui


## Create vocabulary on DB
```shell script
sudo mariadb eoscnode

INSERT IGNORE INTO EOSC_node (id, en, fi)
VALUES (1, 'My EOSC Node', 'My EOSC Node');

INSERT IGNORE INTO accesstypes (id, en, fi)
VALUES (1, 'Open access', 'Open access');

INSERT IGNORE INTO purpose (id, en, fi)
VALUES (1, 'Research', 'Research');

INSERT IGNORE INTO customer_segment (id, en, fi)
VALUES (1, 'Researchers', 'Researchers');

INSERT IGNORE INTO end_user_groups (id, en, fi)
VALUES (1, 'Research communities', 'Research communities');
```

## Insert data into DB
```shell script
INSERT INTO eoscdata (
  avain,
  name_en,
  name_fi,
  tagline_en,
  tagline_fi,
  description_en,
  description_fi,
  website,
  link_to_service_en,
  link_to_service_fi,
  support_email_address,
  service_owner,
  service_provider,
  trl,
  accessTypes,
  nodeId,
  purpose_of_the_service,
  customer_segment,
  end_user_groups
) VALUES (
  'service-001',
  'My first catalog service',
  'My first catalog service',
  'Example service for the EOSC catalog',
  'Example service for the EOSC catalog',
  'This is the first test service published in the local EOSC node catalog.',
  'This is the first test service published in the local EOSC node catalog.',
  'https://example.org',
  'https://example.org/service',
  'https://example.org/service',
  'support@example.org',
  'My Organization',
  'My Organization',
  9,
  1,
  1,
  1,
  1,
  1
);
```

## Add tables
```shell script
INSERT IGNORE INTO br_eoscdata_purpose (palvelu, purpose)
VALUES (1, 1);

INSERT IGNORE INTO br_eoscdata_customer_segment (id, cs_id)
VALUES (1, 1);

INSERT IGNORE INTO br_eoscdata_end_user_groups (id, eug_id)
VALUES (1, 1);
```
