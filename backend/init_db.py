import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://neondb_owner:npg_c3BvLikYtR1P@ep-floral-lab-az4azqky-pooler.c-3.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
)

def init_tables():
    print(f"Connecting to database and running schema migrations...")
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            # 1. Users table (create if not exists or add new columns)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id VARCHAR(64) PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                name VARCHAR(255),
                role VARCHAR(32) NOT NULL DEFAULT 'user',
                tenant_id VARCHAR(64),
                is_guest BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            
            ALTER TABLE users ADD COLUMN IF NOT EXISTS name VARCHAR(255);
            ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(32) NOT NULL DEFAULT 'user';
            ALTER TABLE users ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(64);
            ALTER TABLE users ADD COLUMN IF NOT EXISTS is_guest BOOLEAN NOT NULL DEFAULT FALSE;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
            
            -- Backfill tenant_id for any existing records where tenant_id is NULL
            UPDATE users SET tenant_id = id WHERE tenant_id IS NULL;

            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
            CREATE INDEX IF NOT EXISTS idx_users_tenant_id ON users(tenant_id);
            """)

            # 2. Tenant Documents (Multi-tenant vector & document storage)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS tenant_documents (
                id VARCHAR(64) PRIMARY KEY,
                owner_id VARCHAR(64) NOT NULL,
                filename VARCHAR(255) NOT NULL,
                file_path VARCHAR(512),
                file_size INTEGER DEFAULT 0,
                content TEXT NOT NULL,
                chunk_index INTEGER DEFAULT 0,
                embedding JSONB,
                metadata JSONB DEFAULT '{}'::jsonb,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_tenant_docs_owner_id ON tenant_documents(owner_id);
            CREATE INDEX IF NOT EXISTS idx_tenant_docs_filename ON tenant_documents(filename);
            """)

            # 3. Episodic Memory table
            cur.execute("""
            CREATE TABLE IF NOT EXISTS episodic_memory (
                id VARCHAR(64) PRIMARY KEY,
                owner_id VARCHAR(64) NOT NULL,
                thread_id VARCHAR(64) NOT NULL,
                user_query TEXT NOT NULL,
                assistant_response TEXT NOT NULL,
                intent VARCHAR(64),
                metadata JSONB DEFAULT '{}'::jsonb,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_episodic_owner_id ON episodic_memory(owner_id);
            CREATE INDEX IF NOT EXISTS idx_episodic_thread_id ON episodic_memory(thread_id);
            CREATE INDEX IF NOT EXISTS idx_episodic_created_at ON episodic_memory(created_at DESC);
            """)

            # 4. User Profiles table (Phase 6 Consolidation)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                owner_id VARCHAR(64) PRIMARY KEY,
                profile_summary TEXT,
                summary TEXT,
                interests TEXT,
                travel_preferences JSONB DEFAULT '{}'::jsonb,
                source_doc_count INT DEFAULT 0,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS profile_summary TEXT;
            ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS summary TEXT;
            ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS interests TEXT;
            ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS travel_preferences JSONB DEFAULT '{}'::jsonb;
            ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS source_doc_count INT DEFAULT 0;
            ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
            
            UPDATE user_profiles SET profile_summary = summary WHERE profile_summary IS NULL AND summary IS NOT NULL;

            CREATE INDEX IF NOT EXISTS idx_user_profiles_owner_id ON user_profiles(owner_id);
            """)

            conn.commit()
            print("Successfully migrated and initialized all Neon DB tables: users, tenant_documents, episodic_memory, user_profiles.")

if __name__ == "__main__":
    init_tables()
