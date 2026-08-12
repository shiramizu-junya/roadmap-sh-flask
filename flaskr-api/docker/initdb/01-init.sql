-- テスト専用のデータベースを作り、flaskr ユーザーに権限を与える
CREATE DATABASE IF NOT EXISTS flaskr_test
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON flaskr_test.* TO 'flaskr'@'%';
FLUSH PRIVILEGES;
