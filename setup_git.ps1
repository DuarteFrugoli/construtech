# Start SSH agent and add key
Start-Service ssh-agent
ssh-add $env:USERPROFILE\.ssh\jcjgmail
Write-Host "SSH key added successfully"

# Initialize git if not already initialized
if (-not (Test-Path .git)) {
    git init
    git remote add origin git@github.com:jaumg2004/Construtech.git
    Write-Host "Git repository initialized and remote added"
}

# Add all files and commit
git add .
git commit -m "Initial commit"
Write-Host "Files committed successfully"

# Push to main branch
git push -u origin main
Write-Host "Files pushed to GitHub successfully" 