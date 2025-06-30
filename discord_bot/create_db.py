from models.scheduling import Base, engine

Base.metadata.create_all(engine)
print("Database tables created!")