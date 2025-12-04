#!/bin/bash
echo ">>> Setting up Backend..."
cd backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ">>> Setting up Frontend..."
cd ../frontend
npm install

echo ">>> Setup Complete!"