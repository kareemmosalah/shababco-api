"""Test PostgreSQL connection to Supabase"""
import asyncio
import asyncpg

async def test_connection():
    print("=" * 60)
    print("TESTING POSTGRESQL CONNECTION")
    print("=" * 60)
    print()
    
    try:
        # Connection parameters
        conn = await asyncpg.connect(
            host='aws-1-eu-west-1.pooler.supabase.com',
            port=5432,
            user='postgres.ccwnrsvbvyxbadokhehs',
            password='FkRI6HbzlbefHD5g',
            database='postgres',
            ssl='require',
            timeout=10
        )
        
        print("✅ Connection successful!")
        print()
        
        # Test query
        version = await conn.fetchval('SELECT version();')
        print(f"Database version:")
        print(f"  {version[:80]}...")
        print()
        
        # Test table creation
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS test_connection (
                id SERIAL PRIMARY KEY,
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''')
        print("✅ Table creation test: OK")
        
        # Clean up
        await conn.execute('DROP TABLE test_connection')
        print("✅ Table deletion test: OK")
        print()
        
        await conn.close()
        
        print("=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_connection())
    exit(0 if success else 1)
