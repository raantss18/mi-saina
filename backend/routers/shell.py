from fastapi import APIRouter
from pydantic import BaseModel

from services.shell_exec import execute_command

router = APIRouter()


class ShellRequest(BaseModel):
    command: str
    sudo_password: str | None = None


@router.post("/execute")
async def shell_execute(body: ShellRequest):
    return await execute_command(body.command, body.sudo_password)
