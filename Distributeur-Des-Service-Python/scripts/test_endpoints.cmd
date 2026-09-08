@echo off
chcp 65001 >nul
setlocal
set "B=http://127.0.0.1:8000"
set "P=%~dp0curl_payloads"

echo ============================================
echo Tests curl - Base: %B%
echo Prerequis: python -m uvicorn src.main:app --host 127.0.0.1 --port 8000 (depuis le dossier Distributeur)
echo ============================================
echo.

echo [GET /]
curl -s -w "  [HTTP %%{http_code}]\n" "%B%/"
echo.

echo [GET /test]
curl -s -w "  [HTTP %%{http_code}]\n" "%B%/test"
echo.

echo [GET /api/users]
curl -s -w "  [HTTP %%{http_code}]\n" "%B%/api/users"
echo.

echo [GET /api/users/1]
curl -s -w "  [HTTP %%{http_code}]\n" "%B%/api/users/1"
echo.

echo [POST /api/users]
curl -s -w "  [HTTP %%{http_code}]\n" -X POST "%B%/api/users" -H "Content-Type: application/json" --data-binary "@%P%\user_create.json"
echo.

echo [PUT /api/users/1]
curl -s -w "  [HTTP %%{http_code}]\n" -X PUT "%B%/api/users/1" -H "Content-Type: application/json" --data-binary "@%P%\user_update.json"
echo.

echo [DELETE /api/users/99999]
curl -s -w "  [HTTP %%{http_code}]\n" -X DELETE "%B%/api/users/99999"
echo.

echo [GET /api/history]
curl -s -w "  [HTTP %%{http_code}]\n" "%B%/api/history"
echo.

echo [GET /api/history/1]
curl -s -w "  [HTTP %%{http_code}]\n" "%B%/api/history/1"
echo.

echo [POST /api/history]
curl -s -w "  [HTTP %%{http_code}]\n" -X POST "%B%/api/history" -H "Content-Type: application/json" --data-binary "@%P%\historique_create.json"
echo.

echo [DELETE /api/history/99999]
curl -s -w "  [HTTP %%{http_code}]\n" -X DELETE "%B%/api/history/99999"
echo.

echo [GET /api/conversations/last100]
curl -s -w "  [HTTP %%{http_code}]\n" "%B%/api/conversations/last100"
echo.

echo [GET /api/conversations]
curl -s -w "  [HTTP %%{http_code}]\n" "%B%/api/conversations"
echo.

echo [GET /api/conversations/1]
curl -s -w "  [HTTP %%{http_code}]\n" "%B%/api/conversations/1"
echo.

echo [POST /api/conversations]
curl -s -w "  [HTTP %%{http_code}]\n" -X POST "%B%/api/conversations" -H "Content-Type: application/json" --data-binary "@%P%\conversation_create.json"
echo.

echo [PUT /api/conversations/1]
curl -s -w "  [HTTP %%{http_code}]\n" -X PUT "%B%/api/conversations/1" -H "Content-Type: application/json" --data-binary "@%P%\conversation_update.json"
echo.

echo [DELETE /api/conversations/99999]
curl -s -w "  [HTTP %%{http_code}]\n" -X DELETE "%B%/api/conversations/99999"
echo.

echo [GET /api/notes]
curl -s -w "  [HTTP %%{http_code}]\n" "%B%/api/notes"
echo.

echo [GET /api/notes/1]
curl -s -w "  [HTTP %%{http_code}]\n" "%B%/api/notes/1"
echo.

echo [POST /api/notes]
curl -s -w "  [HTTP %%{http_code}]\n" -X POST "%B%/api/notes" -H "Content-Type: application/json" --data-binary "@%P%\note_create.json"
echo.

echo [PUT /api/notes/1]
curl -s -w "  [HTTP %%{http_code}]\n" -X PUT "%B%/api/notes/1" -H "Content-Type: application/json" --data-binary "@%P%\note_update.json"
echo.

echo [PATCH /api/notes/1/etat]
curl -s -w "  [HTTP %%{http_code}]\n" -X PATCH "%B%/api/notes/1/etat?etat=true"
echo.

echo [DELETE /api/notes/99999]
curl -s -w "  [HTTP %%{http_code}]\n" -X DELETE "%B%/api/notes/99999"
echo.

echo [GET /api/settings]
curl -s -w "  [HTTP %%{http_code}]\n" "%B%/api/settings"
echo.

echo [PUT /api/settings]
curl -s -w "  [HTTP %%{http_code}]\n" -X PUT "%B%/api/settings" -H "Content-Type: application/json" --data-binary "@%P%\setting_update.json"
echo.

echo [GET /api/personal-info]
curl -s -w "  [HTTP %%{http_code}]\n" "%B%/api/personal-info"
echo.

echo [GET /api/personal-info/user/1]
curl -s -w "  [HTTP %%{http_code}]\n" "%B%/api/personal-info/user/1"
echo.

echo [POST /api/personal-info]
curl -s -w "  [HTTP %%{http_code}]\n" -X POST "%B%/api/personal-info" -H "Content-Type: application/json" --data-binary "@%P%\personal_create.json"
echo.

echo [PUT /api/personal-info/1]
curl -s -w "  [HTTP %%{http_code}]\n" -X PUT "%B%/api/personal-info/1" -H "Content-Type: application/json" --data-binary "@%P%\personal_update.json"
echo.

echo [DELETE /api/personal-info/99999]
curl -s -w "  [HTTP %%{http_code}]\n" -X DELETE "%B%/api/personal-info/99999"
echo.

echo [GET /api/accompagnements]
curl -s -w "  [HTTP %%{http_code}]\n" "%B%/api/accompagnements"
echo.

echo [GET /api/accompagnements/user/1]
curl -s -w "  [HTTP %%{http_code}]\n" "%B%/api/accompagnements/user/1"
echo.

echo [GET /api/accompagnements/1]
curl -s -w "  [HTTP %%{http_code}]\n" "%B%/api/accompagnements/1"
echo.

echo [POST /api/accompagnements]
curl -s -w "  [HTTP %%{http_code}]\n" -X POST "%B%/api/accompagnements" -H "Content-Type: application/json" --data-binary "@%P%\accompagnement_create.json"
echo.

echo [PUT /api/accompagnements/1]
curl -s -w "  [HTTP %%{http_code}]\n" -X PUT "%B%/api/accompagnements/1" -H "Content-Type: application/json" --data-binary "@%P%\accompagnement_update.json"
echo.

echo [DELETE /api/accompagnements/99999]
curl -s -w "  [HTTP %%{http_code}]\n" -X DELETE "%B%/api/accompagnements/99999"
echo.

echo [POST /api/auth/login]
curl -s -w "  [HTTP %%{http_code}]\n" -X POST "%B%/api/auth/login" -H "Content-Type: application/json" --data-binary "@%P%\login.json"
echo.

echo [GET /api/auth/registrations]
curl -s -w "  [HTTP %%{http_code}]\n" "%B%/api/auth/registrations"
echo.

echo [GET /api/auth/registrations/999001]
curl -s -w "  [HTTP %%{http_code}]\n" "%B%/api/auth/registrations/999001"
echo.

echo [POST /api/auth/registrations]
curl -s -w "  [HTTP %%{http_code}]\n" -X POST "%B%/api/auth/registrations" -H "Content-Type: application/json" --data-binary "@%P%\auth_create.json"
echo.

echo [PUT /api/auth/registrations/999001]
curl -s -w "  [HTTP %%{http_code}]\n" -X PUT "%B%/api/auth/registrations/999001" -H "Content-Type: application/json" --data-binary "@%P%\auth_update.json"
echo.

echo [DELETE /api/auth/registrations/999001]
curl -s -w "  [HTTP %%{http_code}]\n" -X DELETE "%B%/api/auth/registrations/999001"
echo.

echo [POST /api/trigger-n8n]
curl -s -w "  [HTTP %%{http_code}]\n" -X POST "%B%/api/trigger-n8n" -H "Content-Type: application/json" --data-binary "@%P%\n8n.json"
echo.

echo [GET /api/agendas]
curl -s -w "  [HTTP %%{http_code}]\n" "%B%/api/agendas"
echo.

echo [GET /api/agendas/1]
curl -s -w "  [HTTP %%{http_code}]\n" "%B%/api/agendas/1"
echo.

echo [POST /api/agendas]
curl -s -w "  [HTTP %%{http_code}]\n" -X POST "%B%/api/agendas" -H "Content-Type: application/json" --data-binary "@%P%\agenda_create.json"
echo.

echo [PUT /api/agendas/1]
curl -s -w "  [HTTP %%{http_code}]\n" -X PUT "%B%/api/agendas/1" -H "Content-Type: application/json" --data-binary "@%P%\agenda_update.json"
echo.

echo [DELETE /api/agendas/99999]
curl -s -w "  [HTTP %%{http_code}]\n" -X DELETE "%B%/api/agendas/99999"
echo.

echo [GET /api/activities]
curl -s -w "  [HTTP %%{http_code}]\n" "%B%/api/activities"
echo.

echo [GET /api/activities/1]
curl -s -w "  [HTTP %%{http_code}]\n" "%B%/api/activities/1"
echo.

echo [POST /api/activities]
curl -s -w "  [HTTP %%{http_code}]\n" -X POST "%B%/api/activities" -H "Content-Type: application/json" --data-binary "@%P%\activity_create.json"
echo.

echo [PUT /api/activities/1]
curl -s -w "  [HTTP %%{http_code}]\n" -X PUT "%B%/api/activities/1" -H "Content-Type: application/json" --data-binary "@%P%\activity_update.json"
echo.

echo [DELETE /api/activities/99999]
curl -s -w "  [HTTP %%{http_code}]\n" -X DELETE "%B%/api/activities/99999"
echo.

echo [POST /api/power-off]
curl -s -w "  [HTTP %%{http_code}]\n" -X POST "%B%/api/power-off"
echo.

echo [POST /api/power-on]
curl -s -w "  [HTTP %%{http_code}]\n" -X POST "%B%/api/power-on"
echo.

echo [GET /api/keywords/robot-name]
curl -s -w "  [HTTP %%{http_code}]\n" "%B%/api/keywords/robot-name"
echo.

echo [POST /api/audio/text-to-speech]
curl -s -w "  [HTTP %%{http_code}]\n" -X POST "%B%/api/audio/text-to-speech" -H "Content-Type: application/json" --data-binary "@%P%\tts.json"
echo.

echo --- Multipart (fichier requis) - exemples ---
echo curl -F "file=@photo.jpg" "%B%/api/identify-face"
echo curl -F "file=@audio.wav" "%B%/api/audio/speech-to-text"
echo curl -F "file=@audio.wav" "%B%/api/audio/speech-to-n8n-to-speech"
echo.
echo Termine.
endlocal
