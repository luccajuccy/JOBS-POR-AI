import re

import requests


BASE = "http://127.0.0.1:5000"


def assert_ok(response, label):
    assert response.status_code < 400, f"{label}: {response.status_code} {response.text[:200]}"


def login(email, password="123456"):
    session = requests.Session()
    response = session.post(f"{BASE}/login", data={"email": email, "password": password}, allow_redirects=True)
    assert_ok(response, f"login {email}")
    assert "jobs_session" in session.cookies, f"cookie de sessao ausente para {email}"
    return session


def main():
    candidate = login("candidato2@demo.com")
    company = login("empresa1@demo.com")

    for session, path in [(candidate, "/perfil"), (candidate, "/explorar"), (company, "/empresa"), (candidate, "/dashboard")]:
        response = session.get(f"{BASE}{path}")
        assert_ok(response, path)

    create = company.post(
        f"{BASE}/empresa/vagas",
        data={
            "title": "Vaga Teste Integracao Python",
            "description": "Fluxo automatizado de teste end-to-end.",
            "skills": "python, fastapi, sql",
            "level": "Junior",
            "job_type": "CLT",
            "modality": "Hibrido",
            "salary": "R$ 5.000",
            "address": "Av. Paulista, 1000",
        },
        allow_redirects=True,
    )
    assert_ok(create, "criar vaga")

    explore = candidate.get(f"{BASE}/explorar")
    assert_ok(explore, "explorar depois da vaga")
    match = re.search(r"/vagas/(\d+)/like", explore.text)
    assert match, "nenhum formulario de like encontrado"
    job_id = match.group(1)

    like = candidate.post(f"{BASE}/vagas/{job_id}/like")
    assert_ok(like, "like candidato")
    payload = like.json()
    assert payload["ok"] is True

    company_page = company.get(f"{BASE}/empresa")
    assert_ok(company_page, "empresa candidatos")
    interest = company.post(f"{BASE}/empresa/interesse", data={"candidate_id": 2, "job_id": job_id}, allow_redirects=True)
    assert_ok(interest, "interesse empresa")

    chats = candidate.get(f"{BASE}/chats")
    assert_ok(chats, "chats candidato")
    chat_match = re.search(r"/chats/(\d+)", chats.text)
    assert chat_match, "match nao apareceu no chat do candidato"
    match_id = chat_match.group(1)

    msg1 = candidate.post(f"{BASE}/chats/{match_id}/mensagens", data={"body": "Mensagem do candidato em sessao A."}, allow_redirects=True)
    msg2 = company.post(f"{BASE}/chats/{match_id}/mensagens", data={"body": "Resposta da empresa em sessao B."}, allow_redirects=True)
    assert_ok(msg1, "mensagem candidato")
    assert_ok(msg2, "mensagem empresa")

    api_candidate = candidate.get(f"{BASE}/api/chat/{match_id}").json()
    api_company = company.get(f"{BASE}/api/chat/{match_id}").json()
    bodies_candidate = [m["body"] for m in api_candidate["messages"]]
    bodies_company = [m["body"] for m in api_company["messages"]]
    assert "Mensagem do candidato em sessao A." in bodies_candidate
    assert "Resposta da empresa em sessao B." in bodies_candidate
    assert bodies_candidate == bodies_company

    print("OK: cadastro seed, login, perfil, vagas, likes, match e chat entre duas sessoes foram validados.")


if __name__ == "__main__":
    main()
