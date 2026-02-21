import os
from aiohttp import web
from server import PromptServer
from .nodes.utility_nodes import WWAA_TextFileBrowser

@PromptServer.instance.routes.post("/wwaa/get_text_files")
async def get_text_files(request):
    """
    API endpoint to get list of .csv and .txt files from a directory
    """
    try:
        data = await request.json()
        directory_path = data.get("directory_path", "")
        
        print(f"[API /wwaa/get_text_files] Received request for directory: '{directory_path}'")
        
        files = WWAA_TextFileBrowser.get_files_from_directory(directory_path)
        
        print(f"[API /wwaa/get_text_files] Returning {len(files)} files")
        
        return web.json_response({"files": files})
    except Exception as e:
        print(f"[API /wwaa/get_text_files] Error: {e}")
        import traceback
        traceback.print_exc()
        return web.json_response({"error": str(e), "files": []}, status=500)
