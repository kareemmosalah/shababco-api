import asyncio
import asyncpg

async def test():
    print("=" * 60)
    print("TESTING POSTGRESQL CONNECTION")
    print("=" * 60)
    print()
    
    try:
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
        
        version = await conn.fetchval('SELECT version();')
        print(f"PostgreSQL version:")
        print(f"  {version[:100]}...")
        print()
        
        # Test write
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS connection_test (
                id SERIAL PRIMARY KEY,
                test_time TIMESTAMP DEFAULT NOW()
            )
        ''')
        print("✅ Table creation: OK")
        
        await conn.execute('INSERT INTO connection_test DEFAULT VALUES')
        count = await conn.fetchval('SELECT COUNT(*) FROM connection_test')
        print(f"✅ Insert test: OK (rows: {count})")
        
        await conn.execute('DROP TABLE connection_test')
        print("✅ Cleanup: OK")
        print()
        
        await conn.close()
        
        print("=" * 60)
        print("✅ ALL TESTS PASSED - DATABASE READY!")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
