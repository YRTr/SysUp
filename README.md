Running the Full Stack Locally
Project Directory Structure:

Plaintext
hardware-advisor/
├── backend/
│   ├── scanner.py
│   ├── geo_pricing.py
│   ├── recommender.py
│   └── main.py
└── frontend/
    └── src/
        └── HardwareAdvisor.jsx
Start the Python Backend:

Bash
cd backend
python main.py
(You can also inspect the interactive Swagger docs at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) to test the JSON payloads directly).

Mount the Component in React:
Import <HardwareAdvisor/> inside your Vite or Create-React-App App.jsx file and run npm run dev.