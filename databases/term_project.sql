DROP DATABASE IF EXISTS term_project;
CREATE DATABASE term_project;
USE term_project;

-- 1. User Table (UPDATED: AUTO_INCREMENT)
CREATE TABLE User (
    user_id INT PRIMARY KEY AUTO_INCREMENT, -- CSV ID'leri aynen kalır, yeniler otomatik artar
    name VARCHAR(100),
    email VARCHAR(100),
    password VARCHAR(255),
    Age INT,
    Gender VARCHAR(20) NOT NULL DEFAULT 'Unknown',
    Marital_Status VARCHAR(50) NOT NULL DEFAULT 'Single',
    Occupation VARCHAR(100),
    Monthly_Income VARCHAR(50),
    Educational_Qualifications VARCHAR(100),
    Family_size INT,
    city VARCHAR(50) DEFAULT 'Istanbul',
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. Restaurant Table (UPDATED: AUTO_INCREMENT)
CREATE TABLE Restaurant (
    r_id INT PRIMARY KEY AUTO_INCREMENT, -- CSV ID'leri korunur
    name VARCHAR(100),
    city VARCHAR(50),
    rating DECIMAL(3,1) DEFAULT 0,
    rating_count INT DEFAULT 0,
    cost VARCHAR(50),
    cuisine VARCHAR(100),
    lic_no VARCHAR(100),
    link VARCHAR(255),
    address TEXT,
    menu_json TEXT, 
    secret VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. Food Table (ID String olduğu için AUTO_INCREMENT OLAMAZ)
CREATE TABLE Food (
    f_id VARCHAR(50) PRIMARY KEY,
    item VARCHAR(255),
    veg_or_non_veg VARCHAR(50) NOT NULL DEFAULT 'Non-Veg',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. Menu Table
CREATE TABLE Menu (
    m_id INT PRIMARY KEY AUTO_INCREMENT,
    menu_id VARCHAR(50),
    r_id INT NOT NULL,
    f_id VARCHAR(50) NOT NULL,
    cuisine VARCHAR(100),
    price DECIMAL(10,2) DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (r_id) REFERENCES Restaurant(r_id) ON DELETE CASCADE,
    FOREIGN KEY (f_id) REFERENCES Food(f_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE `Menu`
  ADD CONSTRAINT `chk_price_nonneg`
  CHECK (`price` IS NULL OR `price` >= 0);

ALTER TABLE `Menu`
  ADD KEY `idx_menu_rid` (`r_id`),
  ADD KEY `idx_menu_fid` (`f_id`),
  ADD KEY `idx_menu_price` (`price`),
  ADD KEY `idx_menu_cuisine` (`cuisine`);

-- 5. Courier Table
CREATE TABLE Courier (
    c_id INT PRIMARY KEY AUTO_INCREMENT,
    r_id INT,
    name VARCHAR(50),
    surname VARCHAR(50),
    email VARCHAR(100),
    password VARCHAR(255),
    Age INT,
    Gender VARCHAR(20),
    Marital_Status VARCHAR(50),
    experience INT DEFAULT 0,
    rating DECIMAL(3,1) DEFAULT 0.0,
    ratingCount INT DEFAULT 0,
    taskCount INT DEFAULT 0,
    expected_payment_min DECIMAL(10,2) DEFAULT 100.00,
    expected_payment_max DECIMAL(10,2) DEFAULT 500.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (r_id) REFERENCES Restaurant(r_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. Orders Table
CREATE TABLE Orders (
    o_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    r_id INT NOT NULL,
    order_date DATETIME,
    sales_qty INT DEFAULT 1,
    sales_amount DECIMAL(10,2) NOT NULL DEFAULT 0.0,
    currency VARCHAR(10) DEFAULT 'USD',
    m_id INT NOT NULL,
    c_id INT NOT NULL,
    IsDelivered BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES User(user_id) ON DELETE CASCADE,
    FOREIGN KEY (r_id) REFERENCES Restaurant(r_id) ON DELETE CASCADE,
    FOREIGN KEY (c_id) REFERENCES Courier(c_id) ON DELETE RESTRICT,
    FOREIGN KEY (m_id) REFERENCES Menu(m_id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- -----------------------------------------------------
-- 7. Restaurant_Manager (CSV'de yok, App için gerekli)
-- -----------------------------------------------------
CREATE TABLE Restaurant_Manager (
    rm_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL,
    surname VARCHAR(50),
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    managesId INT, -- Hangi restoranı yönetiyor
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (managesId) REFERENCES Restaurant(r_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- -----------------------------------------------------
-- 8. Positions (CSV'de yok, App için gerekli)
-- Manager tarafından açılan iş ilanları
-- -----------------------------------------------------
CREATE TABLE Positions (
    p_id INT PRIMARY KEY AUTO_INCREMENT,
    r_id INT NOT NULL,
    c_id INT, -- İşe alınan kurye
    city VARCHAR(50),
    req_exp INT DEFAULT 0, -- İstenen deneyim
    req_rating DECIMAL(3,1) DEFAULT 0, -- İstenen minimum rating
    payment DECIMAL(10,2) NOT NULL,
    isOpen BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (c_id) REFERENCES Courier(c_id) ON DELETE SET NULL,
    FOREIGN KEY (r_id) REFERENCES Restaurant(r_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- -----------------------------------------------------
-- 9. Task (CSV'de yok, App Logic'in kalbi)
-- Aktif teslimat görevi
-- -----------------------------------------------------
CREATE TABLE Task (
    t_id INT PRIMARY KEY AUTO_INCREMENT,
    o_id INT NOT NULL, -- Hangi sipariş
    c_id INT NOT NULL, -- Hangi kurye
    user_id INT NOT NULL, -- Kime gidiyor
    m_id INT, -- Ne taşıyor (Nullable yaptık çünkü eski siparişlerin m_id'si yok)
    task_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    user_address TEXT, -- Adres kopyası
    status BOOLEAN DEFAULT FALSE, -- 0: Ongoing, 1: Finished
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (o_id) REFERENCES Orders(o_id) ON DELETE CASCADE,
    FOREIGN KEY (c_id) REFERENCES Courier(c_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES User(user_id) ON DELETE CASCADE,
    FOREIGN KEY (m_id) REFERENCES Menu(m_id) ON DELETE SET NULL,
    UNIQUE KEY unique_order (o_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
