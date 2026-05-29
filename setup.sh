#!/bin/bash

# CheckMate Full Setup Script
# This script installs all required system dependencies for CheckMate

echo "=========================================="
echo "CheckMate Complete Setup Script"
echo "=========================================="
echo ""

# Update package manager
echo "[1/4] Updating package manager..."
sudo apt-get update -qq

# Install system dependencies
echo "[2/4] Installing system dependencies..."
sudo apt-get install -y clangd graphviz perl > /dev/null 2>&1

# Install egypt
echo "[3/4] Installing egypt (call graph generator)..."
cd /tmp
wget https://www.gson.org/egypt/egypt-1.25.tar.gz 2>/dev/null
tar -xzf egypt-1.25.tar.gz
cd egypt-1.25
perl Makefile.PL > /dev/null 2>&1
make > /dev/null 2>&1
sudo make install > /dev/null 2>&1
cd /tmp
rm -rf egypt-1.25 egypt-1.25.tar.gz

# Install fused (optional but needed for fine-tuning)
echo "[4/4] Setting up fused simulator (optional)..."
echo "To install fused, run:"
echo "  git clone https://github.com/rafayy769/fused-checkmate.git"
echo "  cd fused-checkmate"
echo "  bash ../CheckMate/install_fused_script.sh"
echo "  cp build/fused ../CheckMate/fusedBin/"

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env file with your API key:"
echo "   - For Anthropic: ANTHROPIC_API_KEY=your_key"
echo "   - For OpenAI: OPENAI_API_KEY=your_key"
echo "   - Set LLM_MODEL=claude-3-5-sonnet-20241022 (or your preferred model)"
echo ""
echo "2. Verify installation:"
echo "   clangd --version"
echo "   egypt --version"
echo "   dot -V"
echo ""
echo "3. Run CheckMate with a benchmark app:"
echo "   python main.py --bm_name ar-iclib"
echo ""
