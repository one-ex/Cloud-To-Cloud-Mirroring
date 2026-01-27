#!/bin/bash

# Cloud Mirror Bot Setup Script
# Script untuk memudahkan setup awal proyek

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check Python version
check_python() {
    print_info "Checking Python version..."
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | awk '{print $2}')
        print_info "Python $PYTHON_VERSION detected"
        
        # Check if Python 3.9 or higher
        MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
        MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
        
        if [ $MAJOR -lt 3 ] || ([ $MAJOR -eq 3 ] && [ $MINOR -lt 9 ]); then
            print_error "Python 3.9 or higher is required"
            exit 1
        fi
    else
        print_error "Python 3 not found"
        exit 1
    fi
}

# Create virtual environment
create_venv() {
    print_info "Creating virtual environment..."
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        print_info "Virtual environment created"
    else
        print_warning "Virtual environment already exists"
    fi
}

# Install dependencies
install_deps() {
    print_info "Installing dependencies..."
    if [ -d "venv" ]; then
        source venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
        print_info "Dependencies installed"
    else
        print_error "Virtual environment not found"
        exit 1
    fi
}

# Setup environment file
setup_env() {
    print_info "Setting up environment file..."
    if [ ! -f ".env" ]; then
        cp .env.example .env
        print_info "Environment file created. Please edit .env with your configuration"
    else
        print_warning "Environment file already exists"
    fi
}

# Create necessary directories
create_dirs() {
    print_info "Creating necessary directories..."
    mkdir -p logs
    mkdir -p temp
    print_info "Directories created"
}

# Display next steps
show_next_steps() {
    echo -e "\n${GREEN}✅ Setup completed!${NC}"
    echo -e "\n${YELLOW}📋 Next steps:${NC}"
    echo "1. Edit the .env file with your configuration:"
    echo "   - Telegram Bot Token"
    echo "   - Google Drive API credentials"
    echo "   "
    echo "2. Get Google Drive refresh token:"
    echo "   python scripts/get_refresh_token.py"
    echo "   "
    echo "3. Run the application:"
    echo "   source venv/bin/activate"
    echo "   python main.py"
    echo "   "
    echo "4. Test with example URLs:"
    echo "   python test_example.py"
    echo "   "
    echo "5. Deploy to Render:"
    echo "   - Push to GitHub"
    echo "   - Connect repository to Render"
    echo "   - Set environment variables in Render dashboard"
}

# Main setup process
main() {
    echo -e "${GREEN}🚀 Cloud Mirror Bot Setup${NC}"
    echo -e "${GREEN}========================${NC}"
    
    check_python
    create_venv
    install_deps
    setup_env
    create_dirs
    show_next_steps
}

# Run main function
main