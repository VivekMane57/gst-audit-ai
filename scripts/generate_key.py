"""
generate_key.py
---------------
Ek baar run karo — Fernet encryption key generate karo.
Output ko .env mein ENCRYPTION_KEY= ke baad paste karo.

Run: python scripts/generate_key.py
"""
from cryptography.fernet import Fernet

key = Fernet.generate_key().decode()
print("\n" + "=" * 50)
print("ENCRYPTION_KEY (copy this to your .env):")
print("=" * 50)
print(f"\nENCRYPTION_KEY={key}\n")
print("⚠️  Warning: Ye key kabhi GitHub pe push mat karna!")
print("⚠️  Warning: Ek baar set karne ke baad change mat karna.")
print("=" * 50 + "\n")