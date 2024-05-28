# Use an official Python runtime as a parent image
FROM python:3.12-slim AS builder

# Create a non-root user and group
RUN groupadd -r appgroup && useradd -r -g appgroup -d /home/appuser appuser

# Create the /home/appuser directory and set the working directory
RUN mkdir -p /home/appuser && chown appuser:appgroup /home/appuser
WORKDIR /home/appuser

# Copy the current directory contents into the container at /home/appuser
COPY . .

# Change ownership of the working directory to the non-root user
RUN chown -R appuser:appgroup /home/appuser

# Switch to the non-root user
USER appuser

# Modify PATH to include /home/appuser/.local/bin
ENV PATH="/home/appuser/.local/bin:${PATH}"

# Install Poetry
RUN pip install poetry

# Install dependencies and build the project
RUN poetry install --no-root
RUN poetry build

# Use a second stage to create a smaller final image
FROM python:3.12-slim

# Create a non-root user and group
RUN groupadd -r appgroup && useradd -r -g appgroup -d /home/appuser appuser

# Create the /home/appuser directory and set the working directory
RUN mkdir -p /home/appuser && chown appuser:appgroup /home/appuser
WORKDIR /home/appuser

# Copy only the built package from the builder stage
COPY --from=builder /home/appuser/dist/*.whl /home/appuser/

# Change ownership of the working directory to the non-root user
RUN chown -R appuser:appgroup /home/appuser

# Switch to the non-root user
USER appuser

# Modify PATH to include /home/appuser/.local/bin
ENV PATH="/home/appuser/.local/bin:${PATH}"

# Install the built package
RUN pip install /home/appuser/*.whl && rm /home/appuser/*.whl

# Command to run the application
CMD ["hoodwink"]
