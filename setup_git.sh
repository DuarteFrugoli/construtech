#!/bin/bash

# Start SSH agent and add key
eval "$(ssh-agent -s)" && \
ssh-add ~/.ssh/jcjgmail && \
echo "SSH key added successfully"

# Initialize git if not already initialized
if [ ! -d .git ]; then
    git init && \
    git remote add origin git@github.com:jaumg2004/Construtech.git && \
    echo "Git repository initialized and remote added"
fi

# Add all files and commit
git add . && \
git commit -m "Initial commit" && \
echo "Files committed successfully"

# Push to main branch
git push -u origin main && \
echo "Files pushed to GitHub successfully" 