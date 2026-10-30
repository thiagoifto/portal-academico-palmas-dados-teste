#!/usr/bin/env python3
"""R3.20-A1-R3 — Valida um arquivo de contatos no contrato público "diretorio.v1".

Mesmas regras do validador homologado no navegador (R3.20-A1) e do Apps Script (R1): só campos da lista
branca, tipos e tamanhos, texto sem HTML/controle/"javascript:", e-mail institucional, telefones coerentes,
URLs de fonte em domínios permitidos, categorias e cursos existentes, ids únicos. Usado:
  - no build do Portal (scripts/preparar-publicacao.sh), antes de aceitar um arquivo publicado;
  - na verificação automática do repositório de dados de teste.
Sem dependências externas (somente a biblioteca padrão do Python 3).

Uso: python3 scripts/validar-diretorio.py ARQUIVO [--cursos data/portal-content.json] [--somente-ficticios]
Saída: código 0 se válido; 1 com a lista de erros se inválido.
"""
import hashlib, json, re, sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

TAMANHO_MAXIMO = 512 * 1024
CAMPOS_TOPO = {"versao", "gerado_em", "origem", "aviso", "categorias", "contatos", "hash"}
CAMPOS_CONTATO = {"id", "nome", "sigla", "tipo", "categoria", "cursos", "email", "telefones", "whatsapp",
                  "localizacao", "horario", "fonte_url", "fonte_texto", "assuntos"}
TIPOS = {"SETOR", "SERVICO", "CANAL", "COORDENACAO_CURSO"}
HOSTS_FONTE = {"www.ifto.edu.br", "ifto.edu.br", "portal.ifto.edu.br", "suap.ifto.edu.br", "drive.google.com", "wa.me"}
PROIBIDO = re.compile(r"[<>\x00-\x1f\x7f]|javascript:", re.I)
# Cursos do Portal (data/portal-content.json); --cursos substitui esta lista pela do repositório.
CURSOS_PADRAO = {
    "tecnico-em-administracao-ensino-medio-integrado", "tecnico-em-agrimensura-ensino-medio-integrado",
    "tecnico-em-agronegocio-ensino-medio-integrado", "tecnico-em-controle-ambiental-ensino-medio-integrado",
    "tecnico-em-edificacoes-ensino-medio-integrado", "tecnico-em-eletrotecnica-ensino-medio-integrado",
    "tecnico-em-eventos-ensino-medio-integrado", "tecnico-em-informatica-para-internet-ensino-medio-integrado",
    "tecnico-em-mecatronica-ensino-medio-integrado", "tecnico-em-hospedagem-ensino-medio-integrado",
    "tecnico-em-agrimensura-tecnico-subsequente", "tecnico-em-eletrotecnica-tecnico-subsequente",
    "tecnico-em-informatica-tecnico-subsequente", "tecnico-em-secretariado-tecnico-subsequente",
    "tecnico-em-seguranca-do-trabalho-tecnico-subsequente", "tecnico-em-guia-de-turismo-tecnico-subsequente",
    "agronomia-graduacao", "engenharia-civil-graduacao", "engenharia-eletrica-graduacao", "zootecnia-graduacao",
    "licenciatura-em-educacao-fisica-graduacao", "licenciatura-em-fisica-graduacao",
    "licenciatura-em-letras-lingua-portuguesa-graduacao", "licenciatura-em-matematica-graduacao",
    "gestao-do-agronegocio-uab-ifto-graduacao", "gestao-publica-graduacao", "sistemas-para-internet-graduacao",
    "sistemas-fotovoltaicos-pos-graduacao", "tecnologia-ambiental-pos-graduacao",
    "profissional-em-educacao-profissional-e-tecnologica-pos-graduacao", "engenharia-civil-e-ambiental-pos-graduacao",
    "dinter-em-educacao-pci-uel-ifto-pos-graduacao",
}


def texto(valor, maximo, opcional=False):
    if opcional and valor is None:
        return True
    return isinstance(valor, str) and valor.strip() != "" and len(valor) <= maximo and not PROIBIDO.search(valor)


def fonte_url_valida(valor):
    if not isinstance(valor, str) or not valor.startswith("https://") or re.search(r"[\x00-\x20\x7f\\]", valor):
        return False
    try:
        u = urlsplit(valor)
        return not u.username and not u.password and u.port is None and u.hostname in HOSTS_FONTE
    except ValueError:
        return False


def validar_contato(c, categorias, cursos, erros, somente_ficticios):
    rotulo = c.get("id", "?") if isinstance(c, dict) else "?"
    erro = lambda m: erros.append(f"contato {rotulo}: {m}")
    if not isinstance(c, dict):
        return erro("não é um objeto")
    extras = set(c) - CAMPOS_CONTATO
    if extras:
        erro(f"campos não permitidos: {sorted(extras)}")
    if not (isinstance(c.get("id"), str) and re.fullmatch(r"[a-z0-9-]{1,80}", c["id"])):
        erro("id inválido")
    if not texto(c.get("nome"), 200):
        erro("nome ausente ou inválido")
    if c.get("tipo") not in TIPOS:
        erro("tipo inválido")
    if c.get("categoria") not in categorias:
        erro("categoria inexistente")
    if "sigla" in c and not (isinstance(c["sigla"], str) and re.fullmatch(r"[A-Za-zÀ-ÿ0-9-]{1,20}", c["sigla"])):
        erro("sigla inválida")
    for campo, maximo in (("localizacao", 200), ("fonte_texto", 200)):
        if campo in c and not texto(c[campo], maximo):
            erro(f"{campo} inválido")
    if "assuntos" in c and not (isinstance(c["assuntos"], list) and len(c["assuntos"]) <= 30 and all(texto(a, 60) for a in c["assuntos"])):
        erro("assuntos inválidos")
    if "cursos" in c and not (isinstance(c["cursos"], list) and all(isinstance(x, str) and x in cursos for x in c["cursos"])):
        erro("curso inexistente ou lista inválida")
    if "email" in c and not (isinstance(c["email"], str) and re.fullmatch(r"[a-z0-9._-]+@ifto\.edu\.br", c["email"])):
        erro("e-mail fora do padrão institucional")
    if "fonte_url" in c and not fonte_url_valida(c["fonte_url"]):
        erro("fonte_url fora dos domínios permitidos")
    if "telefones" in c:
        tels = c["telefones"]
        if not (isinstance(tels, list) and len(tels) <= 5):
            erro("telefones inválidos")
        else:
            for t in tels:
                ok = isinstance(t, dict) and set(t) <= {"numero", "tel", "rotulo"} \
                    and isinstance(t.get("numero"), str) and re.fullmatch(r"\(\d{2}\) \d{4}-\d{4}", t["numero"]) \
                    and isinstance(t.get("tel"), str) and re.fullmatch(r"\+55\d{10}", t["tel"]) \
                    and t["tel"][3:] == re.sub(r"\D", "", t["numero"]) and t["tel"][5] != "9" \
                    and texto(t.get("rotulo"), 40, opcional=True)
                if not ok:
                    erro("telefone inválido, incoerente ou celular")
    if "whatsapp" in c:
        w = c["whatsapp"]
        if not (isinstance(w, dict) and set(w) <= {"numero", "url"} and texto(w.get("numero"), 30)
                and isinstance(w.get("url"), str) and re.fullmatch(r"https://wa\.me/55\d{10,11}", w["url"])):
            erro("WhatsApp inválido")
    if "horario" in c:
        h = c["horario"]
        if not (isinstance(h, dict) and set(h) <= {"rotulo", "texto"} and texto(h.get("rotulo"), 60) and texto(h.get("texto"), 120)):
            erro("horário inválido")
    if not (c.get("email") or c.get("telefones") or c.get("whatsapp")):
        erro("sem meio de contato")
    if not (c.get("fonte_url") or c.get("fonte_texto")):
        erro("sem fonte")
    if somente_ficticios and not (str(c.get("id", "")).startswith("teste-") and str(c.get("nome", "")).startswith("[TESTE]")):
        erro("modo de teste: só são aceitos contatos fictícios (id 'teste-…' e nome '[TESTE] …')")


def validar(caminho, cursos=None, somente_ficticios=False):
    erros = []
    p = Path(caminho)
    if not p.is_file():
        return [f"arquivo não encontrado: {caminho}"]
    if p.stat().st_size > TAMANHO_MAXIMO:
        return [f"arquivo maior que {TAMANHO_MAXIMO} bytes"]
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        return [f"JSON inválido: {e}"]
    if not isinstance(d, dict):
        return ["a raiz deve ser um objeto"]
    if d.get("versao") != "diretorio.v1":
        erros.append("versao diferente de diretorio.v1")
    extras = set(d) - CAMPOS_TOPO
    if extras:
        erros.append(f"campos de topo não permitidos: {sorted(extras)}")
    cats = d.get("categorias")
    if not (isinstance(cats, dict) and cats and all(re.fullmatch(r"[A-Z_]{1,40}", k) and texto(v, 80) for k, v in cats.items())):
        erros.append("categorias inválidas")
        cats = {}
    for campo, maximo in (("aviso", 300), ("origem", 200)):
        if campo in d and not texto(d[campo], maximo):
            erros.append(f"{campo} inválido")
    if "gerado_em" in d:
        try:
            datetime.fromisoformat(str(d["gerado_em"]).replace("Z", "+00:00"))
        except ValueError:
            erros.append("gerado_em inválido")
    contatos = d.get("contatos")
    if not (isinstance(contatos, list) and 1 <= len(contatos) <= 500):
        erros.append("contatos deve ter de 1 a 500 itens")
        return erros
    ids = [c.get("id") for c in contatos if isinstance(c, dict)]
    if len(set(ids)) != len(contatos):
        erros.append("ids duplicados ou ausentes")
    for c in contatos:
        validar_contato(c, cats, cursos or CURSOS_PADRAO, erros, somente_ficticios)
    if "hash" in d:
        # mesmo cálculo do Apps Script: SHA-256 de JSON.stringify(contatos)
        calculado = hashlib.sha256(json.dumps(contatos, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()
        if d["hash"] != calculado:
            erros.append("hash não corresponde aos contatos")
    return erros


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2
    cursos = None
    if "--cursos" in argv:
        caminho_cursos = argv[argv.index("--cursos") + 1]
        args = [a for a in args if a != caminho_cursos]
        cursos = {c["id"] for c in json.loads(Path(caminho_cursos).read_text(encoding="utf-8"))["cursos"]}
    erros = validar(args[0], cursos, "--somente-ficticios" in argv)
    if erros:
        print(f"INVÁLIDO: {args[0]}")
        for e in erros:
            print(f"  - {e}")
        return 1
    print(f"VÁLIDO: {args[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
