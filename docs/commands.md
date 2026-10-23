Run the Project:
terminal 1:
.\.venv\Scripts\python.exe -c "import uvicorn; uvicorn.run('main:app', app_dir='backend', host='127.0.0.1', port=8001, reload=True)"

terminal 2:
cd frontend
npm run dev
