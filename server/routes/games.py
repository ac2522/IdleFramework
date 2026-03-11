"""Game definition CRUD endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import PlainTextResponse

from idleframework.model.game import GameDefinition
from idleframework.export import to_yaml, to_xml
from server.game_store import game_store
from server.schemas import GameListResponse, GameCreateResponse, GameSummary, ErrorResponse

router = APIRouter()


@router.get("/", response_model=GameListResponse)
def list_games():
    games = game_store.list_games()
    return GameListResponse(games=[GameSummary(**g) for g in games])


@router.get("/{game_id}")
def get_game(game_id: str):
    game = game_store.get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail=ErrorResponse(
            error="game_not_found",
            detail=f"No game with ID '{game_id}' exists",
            status=404,
        ).model_dump())
    return game.model_dump(mode="json")


@router.post("/", response_model=GameCreateResponse, status_code=201)
def create_game(game: GameDefinition):
    game_id = game_store.save_game(game)
    return GameCreateResponse(id=game_id, name=game.name)


@router.delete("/{game_id}", status_code=204)
def delete_game(game_id: str):
    if game_store.is_bundled(game_id):
        raise HTTPException(status_code=403, detail=ErrorResponse(
            error="forbidden",
            detail=f"Cannot delete bundled game '{game_id}'",
            status=403,
        ).model_dump())
    if not game_store.delete_game(game_id):
        raise HTTPException(status_code=404, detail=ErrorResponse(
            error="game_not_found",
            detail=f"No user game with ID '{game_id}' exists",
            status=404,
        ).model_dump())
    return Response(status_code=204)


@router.get("/{game_id}/schema")
def get_schema(game_id: str):
    game = game_store.get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail=ErrorResponse(
            error="game_not_found",
            detail=f"No game with ID '{game_id}' exists",
            status=404,
        ).model_dump())
    return GameDefinition.model_json_schema()


@router.get("/{game_id}/export")
def export_game(game_id: str, format: str = "yaml"):
    game = game_store.get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail=ErrorResponse(
            error="game_not_found",
            detail=f"No game with ID '{game_id}' exists",
            status=404,
        ).model_dump())
    if format == "yaml":
        return PlainTextResponse(to_yaml(game), media_type="text/yaml")
    elif format == "xml":
        return PlainTextResponse(to_xml(game), media_type="application/xml")
    else:
        raise HTTPException(status_code=400, detail=ErrorResponse(
            error="invalid_format",
            detail=f"Unsupported format '{format}'. Use 'yaml' or 'xml'.",
            status=400,
        ).model_dump())
