import os
import boto3
from botocore.client import Config
from fastapi import UploadFile
import uuid
from datetime import datetime

# R2 Storage Configuration
R2_ENDPOINT = "https://2b14c7a1e4dc8693eca31e37d18d416b.r2.cloudflarestorage.com"
R2_ACCESS_KEY_ID = "974014157fee362f486469b8b122aa8d"
R2_SECRET_ACCESS_KEY = "1c0facf8d181f861593c4eb6d979a3d563b26db8d971ead32abc76c6235c592c"
R2_BUCKET_NAME = "azlok-shopping"
R2_PUBLIC_URL = "https://pub-4f4e78fc0ec74271a702caabd7e4e13d.r2.dev"

class R2Storage:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            endpoint_url=R2_ENDPOINT,
            aws_access_key_id=R2_ACCESS_KEY_ID,
            aws_secret_access_key=R2_SECRET_ACCESS_KEY,
            config=Config(signature_version='s3v4')
        )
        self.bucket_name = R2_BUCKET_NAME
        self.public_url = R2_PUBLIC_URL

    async def upload_file(self, file: UploadFile, folder: str = "products") -> dict:
        """
        Upload a file to R2 storage
        
        Args:
            file: The file to upload
            folder: The folder to upload to (default: "products")
            
        Returns:
            dict: Information about the uploaded file
        """
        try:
            # Generate a unique filename
            file_extension = os.path.splitext(file.filename)[1].lower()
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            new_filename = f"{folder}/{timestamp}_{unique_id}{file_extension}"
            
            # Read file content
            file_content = await file.read()
            
            # Upload to R2
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=new_filename,
                Body=file_content,
                ContentType=file.content_type
            )
            
            # Reset file pointer for potential further use
            await file.seek(0)
            
            # Return file information
            return {
                "filename": new_filename,
                "original_filename": file.filename,
                "size": len(file_content),
                "content_type": file.content_type,
                "url": f"{self.public_url}/{new_filename}"
            }
        except Exception as e:
            raise Exception(f"Failed to upload file to R2: {str(e)}")

    def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from R2 storage
        
        Args:
            file_path: The path of the file to delete
            
        Returns:
            bool: True if deletion was successful
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=file_path
            )
            return True
        except Exception as e:
            raise Exception(f"Failed to delete file from R2: {str(e)}")

    def generate_presigned_url(self, file_path: str, expiration: int = 3600) -> str:
        """
        Generate a presigned URL for a file
        
        Args:
            file_path: The path of the file
            expiration: URL expiration time in seconds (default: 1 hour)
            
        Returns:
            str: Presigned URL
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': file_path
                },
                ExpiresIn=expiration
            )
            return url
        except Exception as e:
            raise Exception(f"Failed to generate presigned URL: {str(e)}")

# Create a singleton instance
r2_storage = R2Storage()
