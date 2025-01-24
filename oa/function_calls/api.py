from ninja import NinjaAPI


api = NinjaAPI(urls_namespace="function_calls")


@api.post("/update_vector_store")
def update_vector_store(request, data):
    return {}


@api.get("/create_function")
def create_function(request):
    return {}

