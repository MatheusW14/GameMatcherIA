# 1. Escolhe uma "imagem base" oficial do Python (leve)
FROM python:3.9-slim

# 2. Define qual será a pasta de trabalho dentro do container
WORKDIR /app

# 3. Copia o arquivo de dependências da sua máquina para o container
COPY requirements.txt .

# 4. Instala as dependências dentro do container
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copia todo o resto do código da sua máquina para o container
COPY . .

# 6. Avisa que o container vai se comunicar na porta 5000 (padrão do Flask)
EXPOSE 5000

# 7. O comando que o container vai executar quando ligar
CMD ["python", "app.py"]