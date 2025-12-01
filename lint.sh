(
    printf "\033[34mRunning \`ruff format .\` .. \033[0m\n" && \
    ruff format . && \
    printf "\n\033[34mRunning \`ruff check . --fix\` .. \033[0m\n" && \
    ruff check . --fix && \
    printf "\n\033[34mRunning \`mypy src\` .. \033[0m\n" && \
    mypy src
)