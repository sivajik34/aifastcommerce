from pydantic import BaseModel


class GetCountryInput(BaseModel):
    country_id: str
  