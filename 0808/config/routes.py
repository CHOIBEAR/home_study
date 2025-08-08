from fastapi import APIRouter
from controller.root import apps
ctrs = []
for link in apps:
  route = APIRouter()
  router = {
    "prefix": link["prefix"],
    "tags": link["tags"],
  }
  for item in link["urls"]:
    route.add_api_route(**item)
    
  router["router"] = route
  ctrs.append(router)