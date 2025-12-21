import pandas as pd
import mysql.connector
from mysql.connector import Error
import numpy as np
import os
import time

import dotenv
dotenv.load_dotenv()

# ---------------------------------------------------------
# AYARLAR
# ---------------------------------------------------------
CSV_FOLDER_PATH = 'raw_data'
BATCH_SIZE = 2000

db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': os.getenv("DB_PASSWORD"), # <-- ŞİFRENİ YAZ
    'database': 'term_project',
    'ssl_disabled': True,
    'allow_local_infile': True
}

# Hafızada tutulacak Menü Haritası {r_id: (m_id, price)}
MENU_MAP = {}

# ---------------------------------------------------------
# BAĞLANTI VE YARDIMCI FONKSİYONLAR
# ---------------------------------------------------------
def create_connection():
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except Error as e:
        print(f"Veritabanı bağlantı hatası: {e}")
        return None

def insert_data_in_batches(cursor, conn, query, data, table_name):
    if not data:
        print(f"--- {table_name}: Yüklenecek veri yok! ---")
        return
        
    total_rows = len(data)
    print(f"--- {table_name}: Toplam {total_rows} satır yükleniyor... ---")
    
    start_time = time.time()
    
    for i in range(0, total_rows, BATCH_SIZE):
        batch = data[i:i + BATCH_SIZE]
        try:
            cursor.executemany(query, batch)
            conn.commit()
            percent = min(100, round(((i + BATCH_SIZE) / total_rows) * 100))
            print(f"\rYükleniyor: %{percent} ({min(i + BATCH_SIZE, total_rows)} / {total_rows})", end='')
        except Error as e:
            print(f"\n HATA (Batch {i}): {e}")
            continue
            
    end_time = time.time()
    print(f"\n{table_name} tamamlandı. Süre: {round(end_time - start_time, 2)} sn.\n")

def get_csv_path(filename):
    return os.path.join(CSV_FOLDER_PATH, filename)

# ---------------------------------------------------------
# TABLO YÜKLEME FONKSİYONLARI
# ---------------------------------------------------------

def create_legacy_courier(cursor, conn):
    print("--- Legacy Courier (ID 1) Oluşturuluyor ---")
    # Bu kurye tüm eski CSV siparişlerini üstlenecek
    # r_id NULL (Freelancer gibi düşünebiliriz veya herhangi birine bağlı)
    query = """
    INSERT IGNORE INTO Courier 
    (c_id, r_id, name, surname, email, password, Age, Gender, Marital_Status, experience, rating, ratingCount, taskCount) 
    VALUES 
    (1, NULL, 'Legacy', 'System', 'legacy@sys.com', 'admin123', 99, 'Bot', 'Single', 10, 5.0, 99999, 99999)
    """
    try:
        cursor.execute(query)
        conn.commit()
        print("Başarılı: Legacy Courier eklendi.")
    except Error as e:
        print(f"Legacy Courier hatası: {e}")

def import_food(cursor, conn):
    file_path = get_csv_path('food.csv')
    try:
        df = pd.read_csv(file_path)
        # NULL KONTROLÜ: Veg/Non-Veg boşsa 'Non-Veg' yap
        df['veg_or_non_veg'] = df['veg_or_non_veg'].fillna('Non-Veg')
        df = df.where(pd.notnull(df), None)
        
        data = df[['f_id', 'item', 'veg_or_non_veg']].values.tolist()
        query = "INSERT IGNORE INTO Food (f_id, item, veg_or_non_veg) VALUES (%s, %s, %s)"
        insert_data_in_batches(cursor, conn, query, data, "Food")
    except Exception as e:
        print(f"Food hata: {e}")

def import_users(cursor, conn):
    file_path = get_csv_path('users.csv')
    try:
        df = pd.read_csv(file_path)
        df.rename(columns={
            'Marital Status': 'Marital_Status', 
            'Monthly Income': 'Monthly_Income',
            'Educational Qualifications': 'Educational_Qualifications',
            'Family size': 'Family_size'
        }, inplace=True)
        
        # NULL KONTROLÜ: Gender ve Marital Status
        df['Gender'] = df['Gender'].fillna('Unknown')
        df['Marital_Status'] = df['Marital_Status'].fillna('Single')
        
        # Diğer boşluklar için None
        df = df.where(pd.notnull(df), None)

        cols = ['user_id', 'name', 'email', 'password', 'Age', 'Gender', 
                'Marital_Status', 'Occupation', 'Monthly_Income']
        
        data = df[cols].values.tolist()
        query = """
        INSERT IGNORE INTO User 
        (user_id, name, email, password, Age, Gender, Marital_Status, Occupation, Monthly_Income) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        insert_data_in_batches(cursor, conn, query, data, "User")
    except Exception as e:
        print(f"User hata: {e}")

def import_restaurants(cursor, conn):
    file_path = get_csv_path('restaurant.csv')
    try:
        df = pd.read_csv(file_path, low_memory=False)
        df.rename(columns={'id': 'r_id'}, inplace=True)
        df['rating'] = pd.to_numeric(df['rating'], errors='coerce').fillna(0.0)
        df['rating_count'] = df['rating_count'].astype(str).str.extract(r'(\d+)').fillna(0).astype(int)
        df['cuisine'] = df['cuisine'].astype(str).apply(lambda x: x.split(',')[0].strip())

        df = df.where(pd.notnull(df), None)

        cols = ['r_id', 'name', 'city', 'rating', 'rating_count', 'cost',
                'cuisine', 'lic_no', 'link', 'address']

        data = df[cols].values.tolist()
        query = """
        INSERT IGNORE INTO Restaurant
        (r_id, name, city, rating, rating_count, cost, cuisine, lic_no, link, address)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        insert_data_in_batches(cursor, conn, query, data, "Restaurant")
    except Exception as e:
        print(f"Restaurant hata: {e}")
def import_couriers(cursor, conn):
    # CSV'den gelen gerçek kuryeler (ID 1'den sonrasına eklenecekler çünkü ID 1'i biz aldık)
    file_path = get_csv_path('couriers.csv')
    try:
        df = pd.read_csv(file_path)
        df.rename(columns={'MaritalStatus': 'Marital_Status'}, inplace=True)
        df['rating'] = pd.to_numeric(df['rating'], errors='coerce').fillna(0.0)
        df['ratingCount'] = pd.to_numeric(df['ratingCount'], errors='coerce').fillna(0).astype(int)
        df['taskCount'] = pd.to_numeric(df['taskCount'], errors='coerce').fillna(0).astype(int)
        df['experience'] = pd.to_numeric(df['experience'], errors='coerce').fillna(0).astype(int)
        df.replace({np.nan: None}, inplace=True)
        
        # c_id AUTO_INCREMENT olduğu için CSV'den okumuyoruz veya
        # eğer CSV'de c_id yoksa sorun yok.
        cols = ['r_id', 'name', 'surname', 'email', 'password', 'Age', 'Gender', 
                'Marital_Status', 'experience', 'rating', 'ratingCount', 'taskCount']
        
        data = df[cols].values.tolist()
        query = """
        INSERT IGNORE INTO Courier 
        (r_id, name, surname, email, password, Age, Gender, Marital_Status, experience, rating, ratingCount, taskCount) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        insert_data_in_batches(cursor, conn, query, data, "Courier")
    except Exception as e:
        print(f"Courier hata: {e}")

def import_menu_and_build_map(cursor, conn):
    # Hem Menüyü yükler hem de MENU_MAP'i doldurur
    print("--- Menu Tablosu Yükleniyor ve Haritalanıyor ---")
    file_path = get_csv_path('menu.csv')
    try:
        df = pd.read_csv(file_path, low_memory=False)
        df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0.0)
        df = df.where(pd.notnull(df), None)
        
        # DB'ye Yükleme
        cols = ['menu_id', 'r_id', 'f_id', 'cuisine', 'price']
        data = df[cols].values.tolist()
        
        query = "INSERT IGNORE INTO Menu (menu_id, r_id, f_id, cuisine, price) VALUES (%s, %s, %s, %s, %s)"
        insert_data_in_batches(cursor, conn, query, data, "Menu")
        
        # Haritalama (Orders için)
        # Her restoran için İLK menü öğesini alacağız
        # DB'den çekmek daha güvenli çünkü auto_increment m_id'leri orada oluştu
        print("--- Menü Haritası Oluşturuluyor (SQL'den çekiliyor)... ---")
        cursor.execute("SELECT r_id, m_id, price FROM Menu")
        rows = cursor.fetchall()
        
        global MENU_MAP
        count = 0
        for r_id, m_id, price in rows:
            # Eğer bu restoran haritada yoksa ekle (Yani restoranın ilk menü itemi varsayılan olur)
            if r_id not in MENU_MAP:
                MENU_MAP[r_id] = {'m_id': m_id, 'price': float(price) if price else 0.0}
                count += 1
        print(f"--- Menü Haritası Hazır: {count} restoran için menü bulundu ---")
        
    except Exception as e:
        print(f"Menu hata: {e}")

def import_orders_with_logic(cursor, conn):
    print("--- Orders Tablosu İşleniyor (Mapping Logic) ---")
    file_path = get_csv_path('orders.csv')
    try:
        df = pd.read_csv(file_path, low_memory=False)
        df['order_date'] = pd.to_datetime(df['order_date'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
        
        processed_data = []
        skipped_count = 0
        
        # Pandas satırlarında dönüyoruz
        for _, row in df.iterrows():
            r_id = row['r_id']
            qty = row['sales_qty'] if pd.notnull(row['sales_qty']) else 1
            
            # 1. Bu restoranın menüsü var mı?
            if r_id in MENU_MAP:
                menu_item = MENU_MAP[r_id]
                m_id = menu_item['m_id']
                price = menu_item['price']
                
                # 2. Yeni Tutar Hesapla
                new_amount = float(qty) * price
                
                # 3. Veriyi Hazırla (c_id = 1 SABİT)
                processed_data.append([
                    row['user_id'], 
                    r_id, 
                    row['order_date'], 
                    qty, 
                    new_amount, 
                    row['currency'],
                    m_id,  # Bulduğumuz m_id
                    1      # Legacy Courier ID
                ])
            else:
                # Menüsü olmayan restoranın siparişini atlıyoruz (Çünkü m_id NOT NULL)
                skipped_count += 1

        print(f"--- İşlenen Sipariş: {len(processed_data)}, Atlanan (Menüsü Yok): {skipped_count} ---")
        
        query = """
        INSERT IGNORE INTO Orders 
        (user_id, r_id, order_date, sales_qty, sales_amount, currency, m_id, c_id, IsDelivered) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1)
        """
        insert_data_in_batches(cursor, conn, query, processed_data, "Orders")
        
    except Exception as e:
        print(f"Orders hata: {e}")

# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
def main():
    conn = create_connection()
    if conn is None:
        return
    
    cursor = conn.cursor()
    
    try:
        # Hazırlık
        cursor.execute("SET FOREIGN_KEY_CHECKS=0;")
        cursor.execute("SET SQL_MODE='NO_AUTO_VALUE_ON_ZERO';")
        print("--- BAŞLIYOR ---")

        # 1. Önce Bağımsızlar ve Legacy Courier
        create_legacy_courier(cursor, conn) # ID 1 oluştu
        import_food(cursor, conn)
        import_users(cursor, conn)
        import_restaurants(cursor, conn)
        import_couriers(cursor, conn) # Diğer kuryeler (ID 2, 3...)
        
        # 2. Menüleri Yükle ve Hafızaya Al
        import_menu_and_build_map(cursor, conn)
        
        # 3. Siparişleri Menüye Göre İşle ve Yükle
        import_orders_with_logic(cursor, conn)
        
        cursor.execute("SET FOREIGN_KEY_CHECKS=1;")
        print("\n--- BİTTİ: Tüm veriler mantıksal bağlarla yüklendi! ---")
        
    except Exception as e:
        print(f"Beklenmedik hata: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main()