from ssn.memory.semantic_store import SemanticStore


if __name__ == "__main__":
    store = SemanticStore()

    print("Setting fact...")
    store.set("samson.favorite_color", "blue")

    print("Reading fact...")
    print(store.get("samson.favorite_color"))

    print("All facts:")
    print(store.all())

    print("Deleting...")
    store.delete("samson.favorite_color")

    print("After delete:")
    print(store.get("samson.favorite_color"))
