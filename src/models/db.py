from sqlmodel import Field, Session, SQLModel, create_engine

from src.conf import POSTGRES_JDBC_URL


class Models(SQLModel, table=True):
    id: str = Field(primary_key=True, unique=True, index=True)
    func: str
    definition: list


engine = create_engine(url=POSTGRES_JDBC_URL, echo=True)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


if __name__ == "__main__":
    create_db_and_tables()
