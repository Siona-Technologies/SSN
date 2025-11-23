from ssn.security.vault import Vault

v = Vault()

print("Storing secret...")
v.store("samson_pin", "1234")

print("Reading secret...")
print(v.retrieve("samson_pin"))

print("Deleting...")
v.delete("samson_pin")

print("Reading after delete:")
print(v.retrieve("samson_pin"))
