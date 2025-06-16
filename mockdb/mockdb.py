import pandas as pd
import mysql.connector
from faker import Faker
import os

# --- Configuration ---
DB_HOST = '127.0.0.1'
DB_PORT = 5455
DB_USER = 'root'        # RCM 用户名
DB_PASSWORD = 'infini_rag_flow'  # RCM 密码
DB_NAME = 'mockdb'      # RCM 数据库名

PROJECTS_FILENAME_CSV = 'projects.xlsx - Sheet1.csv'
PROJECT_MEMBERS_FILENAME_CSV = 'project_members.xlsx - Sheet1.csv'

# --- Column Name Mappings ---
# For 'projects.xlsx - Sheet1.csv' (columns B-L)
PROJECTS_COLUMNS_B_L_MAP = {
    '投资项目编号': 'project_id',
    '项目名称': 'project_name',
    '项目类型': 'project_type',
    '土地使用税': 'land_use_tax',
    '项目地址': 'project_address',
    '项目占地面积': 'project_area',
    '启动时间': 'start_date',
    '项目投资额': 'investment_amount',
    '项目建设规模': 'construction_scale',
    '决议时间': 'resolution_date',
    '备案号': 'filing_number'
}

# For 'project_members.xlsx - Sheet1.csv'
# Based on your provided headers: 项目编码, 项目名称, 角色, 姓名
MEMBERS_COLUMN_MAP = {
    '项目编码': 'project_id',
    '项目名称': 'member_project_name', # Using a distinct name for project name from members file
    '角色': 'role',
    '姓名': 'member_name'
}

# Define which column (using its CHINESE name from CSV) is the project identifier
ACTUAL_PROJECT_ID_COL_IN_PROJECTS_CSV = '投资项目编号'
ACTUAL_PROJECT_ID_COL_IN_MEMBERS_CSV = '项目编码'
ACTUAL_MEMBER_NAME_COL_IN_MEMBERS_CSV = '姓名'


# Desired English names for key columns in the Database
DB_PROJECT_ID_COL_NAME = PROJECTS_COLUMNS_B_L_MAP.get(ACTUAL_PROJECT_ID_COL_IN_PROJECTS_CSV, 'project_id')
DB_MEMBER_NAME_COL_NAME = MEMBERS_COLUMN_MAP.get(ACTUAL_MEMBER_NAME_COL_IN_MEMBERS_CSV, 'member_name')
DB_PROJECT_ID_FK_COL_NAME = MEMBERS_COLUMN_MAP.get(ACTUAL_PROJECT_ID_COL_IN_MEMBERS_CSV, 'project_id')


# Initialize Faker for generating random CHINESE names
fake = Faker('zh_CN')

def get_script_directory():
    return os.path.dirname(os.path.abspath(__file__))

def generate_random_name():
    """Generates a random Chinese name."""
    return fake.name()

def main():
    script_dir = get_script_directory()
    projects_filepath = os.path.join(script_dir, PROJECTS_FILENAME_CSV)
    members_filepath = os.path.join(script_dir, PROJECT_MEMBERS_FILENAME_CSV)

    # --- 1. Read Projects Data (with Chinese headers) ---
    print(f"Attempting to read projects data from: {projects_filepath}")
    try:
        df_projects_full_chinese = pd.read_csv(projects_filepath, encoding='utf-8')
    except FileNotFoundError:
        print(f"ERROR: File '{projects_filepath}' not found.")
        return
    except Exception as e:
        print(f"ERROR reading '{projects_filepath}': {e}")
        return

    if df_projects_full_chinese.shape[1] < 12:
        print(f"ERROR: '{PROJECTS_FILENAME_CSV}' has fewer than 12 columns (A-L).")
        return

    df_projects_selected_chinese = df_projects_full_chinese.iloc[:, 1:12].copy()
    actual_b_l_column_names_chinese = df_projects_selected_chinese.columns.tolist()
    print(f"Actual Chinese column names from B-L in '{PROJECTS_FILENAME_CSV}': {actual_b_l_column_names_chinese}")

    df_projects_eng_cols = {}
    valid_projects_mapping = True
    for chinese_col_name in actual_b_l_column_names_chinese:
        if chinese_col_name not in PROJECTS_COLUMNS_B_L_MAP:
            print(f"ERROR: Chinese column '{chinese_col_name}' from '{PROJECTS_FILENAME_CSV}' (B-L) is not defined in PROJECTS_COLUMNS_B_L_MAP.")
            valid_projects_mapping = False
        else:
            df_projects_eng_cols[PROJECTS_COLUMNS_B_L_MAP[chinese_col_name]] = df_projects_selected_chinese[chinese_col_name]

    if not valid_projects_mapping: return
    df_projects_eng = pd.DataFrame(df_projects_eng_cols)

    if ACTUAL_PROJECT_ID_COL_IN_PROJECTS_CSV not in actual_b_l_column_names_chinese:
        print(f"ERROR: Designated Chinese project ID '{ACTUAL_PROJECT_ID_COL_IN_PROJECTS_CSV}' not found in B-L columns: {actual_b_l_column_names_chinese}")
        return
    if DB_PROJECT_ID_COL_NAME not in df_projects_eng.columns:
        print(f"ERROR: Project ID column '{ACTUAL_PROJECT_ID_COL_IN_PROJECTS_CSV}' mapped to '{DB_PROJECT_ID_COL_NAME}' not in processed English project columns.")
        return
        
    print(f"Successfully read and mapped columns for '{PROJECTS_FILENAME_CSV}'. English columns: {df_projects_eng.columns.tolist()}")

    # --- 2. Read Project Members Data (with Chinese headers) ---
    print(f"Attempting to read project members data from: {members_filepath}")
    try:
        df_members_chinese = pd.read_csv(members_filepath, encoding='utf-8')
    except FileNotFoundError:
        print(f"ERROR: File '{members_filepath}' not found.")
        return
    except Exception as e:
        print(f"ERROR reading '{members_filepath}': {e}")
        return

    df_members_eng_cols = {}
    valid_members_mapping = True
    for chinese_col_name, english_col_name in MEMBERS_COLUMN_MAP.items():
        if chinese_col_name not in df_members_chinese.columns:
            print(f"WARNING: Chinese column '{chinese_col_name}' (mapped to '{english_col_name}') not found in '{PROJECT_MEMBERS_FILENAME_CSV}'. It will be skipped.")
            if chinese_col_name in [ACTUAL_PROJECT_ID_COL_IN_MEMBERS_CSV, ACTUAL_MEMBER_NAME_COL_IN_MEMBERS_CSV]:
                print(f"ERROR: Essential Chinese column '{chinese_col_name}' not found in '{PROJECT_MEMBERS_FILENAME_CSV}'.")
                valid_members_mapping = False
        else:
            df_members_eng_cols[english_col_name] = df_members_chinese[chinese_col_name]
    
    if not valid_members_mapping: return
    df_members_eng = pd.DataFrame(df_members_eng_cols)

    if DB_PROJECT_ID_FK_COL_NAME not in df_members_eng.columns:
        print(f"ERROR: Project ID FK column (expected '{DB_PROJECT_ID_FK_COL_NAME}') not in mapped English members columns.")
        print(f"Ensure '{ACTUAL_PROJECT_ID_COL_IN_MEMBERS_CSV}' is in MEMBERS_COLUMN_MAP and CSV file.")
        return
    if DB_MEMBER_NAME_COL_NAME not in df_members_eng.columns:
        print(f"ERROR: Member name column (expected '{DB_MEMBER_NAME_COL_NAME}') not in mapped English members columns.")
        print(f"Ensure '{ACTUAL_MEMBER_NAME_COL_IN_MEMBERS_CSV}' is in MEMBERS_COLUMN_MAP and CSV file.")
        return

    df_members_eng[DB_MEMBER_NAME_COL_NAME] = [generate_random_name() for _ in range(len(df_members_eng))]
    print(f"Successfully read and mapped columns for '{PROJECT_MEMBERS_FILENAME_CSV}'. English columns: {df_members_eng.columns.tolist()}")
    print(f"Names in '{DB_MEMBER_NAME_COL_NAME}' column replaced with random Chinese names.")

    # --- 3. Database Operations ---
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD)
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.execute(f"USE `{DB_NAME}`")
        print(f"Successfully connected to database and selected/created '{DB_NAME}'.")

        # Create 'projects' table
        project_table_cols_sql = [f"`{DB_PROJECT_ID_COL_NAME}` VARCHAR(255) NOT NULL PRIMARY KEY"]
        for col_name_eng in df_projects_eng.columns:
            if col_name_eng != DB_PROJECT_ID_COL_NAME:
                project_table_cols_sql.append(f"`{col_name_eng}` TEXT")
        create_projects_table_sql = f"CREATE TABLE IF NOT EXISTS projects ({', '.join(project_table_cols_sql)}) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"
        cursor.execute(create_projects_table_sql)
        print(f"Table 'projects' checked/created. Columns: {df_projects_eng.columns.tolist()}")

        # Create 'project_members' table
        members_table_cols_sql = ["`id` INT AUTO_INCREMENT PRIMARY KEY"]
        for col_name_eng in df_members_eng.columns:
            col_cleaned = f"`{col_name_eng}`"
            if col_name_eng == DB_PROJECT_ID_FK_COL_NAME:
                members_table_cols_sql.append(f"{col_cleaned} VARCHAR(255) NOT NULL")
            else:
                members_table_cols_sql.append(f"{col_cleaned} TEXT")
        fk_sql = (f"FOREIGN KEY (`{DB_PROJECT_ID_FK_COL_NAME}`) REFERENCES `projects`(`{DB_PROJECT_ID_COL_NAME}`) "
                  f"ON DELETE CASCADE ON UPDATE CASCADE")
        members_table_cols_sql.append(fk_sql)
        create_project_members_table_sql = f"CREATE TABLE IF NOT EXISTS project_members ({', '.join(members_table_cols_sql)}) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"
        cursor.execute(create_project_members_table_sql)
        print(f"Table 'project_members' checked/created. Columns: {df_members_eng.columns.tolist()}")

        # Insert data into 'projects'
        project_cols_for_insert_eng = [f"`{col}`" for col in df_projects_eng.columns]
        project_placeholders = ', '.join(['%s'] * len(df_projects_eng.columns))
        update_clause_parts = [f"{col}=VALUES({col})" for col in project_cols_for_insert_eng if col != f"`{DB_PROJECT_ID_COL_NAME}`"]
        if update_clause_parts:
             sql_insert_project = (f"INSERT INTO projects ({', '.join(project_cols_for_insert_eng)}) VALUES ({project_placeholders}) "
                                   f"ON DUPLICATE KEY UPDATE {', '.join(update_clause_parts)}")
        else:
             sql_insert_project = (f"INSERT IGNORE INTO projects ({', '.join(project_cols_for_insert_eng)}) VALUES ({project_placeholders})")
        project_data_tuples = [tuple(x) for x in df_projects_eng.where(pd.notnull(df_projects_eng), None).values]
        if project_data_tuples:
            cursor.executemany(sql_insert_project, project_data_tuples)
            print(f"Successfully inserted/updated {len(project_data_tuples)} records into 'projects' table.")
        else: print("No data from projects file to insert.")

        # Insert data into 'project_members'
        member_cols_for_insert_eng = [f"`{col}`" for col in df_members_eng.columns]
        member_placeholders = ', '.join(['%s'] * len(df_members_eng.columns))
        sql_insert_member = f"INSERT INTO project_members ({', '.join(member_cols_for_insert_eng)}) VALUES ({member_placeholders})"
        member_data_tuples = [tuple(x) for x in df_members_eng.where(pd.notnull(df_members_eng), None).values]
        if member_data_tuples:
            cursor.executemany(sql_insert_member, member_data_tuples)
            print(f"Successfully inserted {len(member_data_tuples)} records into 'project_members' table.")
        else: print("No data from project members file to insert.")

        conn.commit()
        print("Data import completed successfully!")

    except mysql.connector.Error as err:
        print(f"MySQL Error: {err}")
        if conn: conn.rollback(); print("Transaction rolled back.")
    except pd.errors.EmptyDataError:
        print("ERROR: One of the CSV files is empty or not correctly formatted.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        if conn: conn.rollback(); print("Transaction rolled back due to unexpected error.")
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close(); print("Database connection closed.")

if __name__ == '__main__':
    main()
