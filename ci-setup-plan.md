# CI/CD reaproveitável para os mods de mc-mods

## Contexto

Hoje 12 projetos carregam cópias quase idênticas de um template com 3 workflows (`auto-tag.yml`, `pr-checks.yml`, `release-on-tag.yml`, ex.: `ae2-cloud/.github/workflows/`). Eles divergem só em: JDKs, tasks Gradle, glob dos jars por subprojeto, título e origem das notas. Publicam só em GitHub Releases, com actions v4. O único upload pro CurseForge é o `copycat-replace/.github/workflows/build.yml` (`itsmeow/curseforge-upload`, token em secret de repo). Outros 7 projetos não têm CI.

Objetivo: um único repositório de CI versionado, que todos os mods chamam por meio de 3 workflows "caller" finos e um arquivo de config por repo. Fluxo:

- **PR**: testes + build de todos os loaders.
- **Merge na main**: cria a tag `v<mod_version>`.
- **Tag**: build → aprovação manual → publish automático no CurseForge.

Decisões já tomadas:
- Repos **públicos** na org, o que libera environments com required reviewers e secrets de org no plano Free.
- Versão vem do **`gradle.properties` `mod_version`**.
- Publicar **só no CurseForge**.

Este plano define só a estrutura. Onboarding dos projetos fica fora do escopo agora.

## Fatos que moldam o design

- **CurseForge não tem OIDC nem trusted publishing.** O upload só aceita API token estático. A alternativa à OIDC é um secret de org `CURSEFORGE_TOKEN`, liberado para repos selecionados e usado apenas no job protegido pelo environment.
- **Tag criada com `GITHUB_TOKEN` não dispara outros workflows.** O template atual contorna isso chamando o release via `workflow_call`. Para que "criar tag ⇒ release" funcione também com tags manuais, a tag é criada com o token de uma **GitHub App da org**, via `actions/create-github-app-token`.
- **Environment em reusable workflow** é declarado no job do workflow chamado, mas resolvido no repo chamador. Por isso cada mod precisa de um environment `curseforge`, criado por script. Em repo público, required reviewers e deployment tag policy funcionam no plano Free.
- **Uma aprovação libera todos os jobs da matrix** que estão esperando o mesmo environment, então é um clique por release.

## Actions escolhidas (todas oficiais ou comunidade ativa, versões de nov/2026)

| Uso | Action | Versão |
|---|---|---|
| checkout | `actions/checkout` | v7 (7.0.1) |
| JDKs | `actions/setup-java` (temurin, lista 17/21/25) | v6 (6.1.0) |
| Gradle, cache e validação do wrapper | `gradle/actions/setup-gradle` | v6 (6.4.1) |
| artefatos | `actions/upload-artifact` / `download-artifact` | major atual |
| token da App | `actions/create-github-app-token` | v3 (3.3.0) |
| upload CurseForge | `Kira-NT/mc-publish` (ex-Kir-Antipov), só destino `curseforge` | v3.3.2 (out/2026), **pinado por SHA** |
| lint do próprio repo de CI | `rhysd/actionlint` + `zizmor` (zizmorcore/zizmor-action) | atual |

O fallback para o upload, se o mc-publish parar de ser mantido, é `itsmeow/curseforge-upload`, já usado no copycat-replace. A troca fica isolada em um único step do `mod-release.yml`.

Regras de pin:
- Actions oficiais por major tag. Terceiros por SHA com comentário da versão.
- Dependabot (`github-actions`) no repo de CI e em cada mod mantém tudo atualizado.

## Estrutura do repositório central `<org>/mc-ci`

Clone local em `mc-mods/mc-ci/`. É um repo dedicado, separado do `<org>/.github`, para ter versionamento e CI próprios.

```
mc-ci/
  .github/workflows/
    mod-ci.yml        # workflow_call — PR: testes + build por target + preview de release
    mod-tag.yml       # workflow_call — push na default branch: cria tag v<mod_version>
    mod-release.yml   # workflow_call — tag: valida, builda, aprova, publica no CurseForge
    self-test.yml     # CI do próprio mc-ci: actionlint, zizmor, testes dos scripts
  actions/
    setup-build/action.yml   # composite: setup-java (multi-JDK) + setup-gradle + toolchains
    read-config/action.yml   # composite: lê/valida .github/mod-pipeline.json, emite matrix e versão
  scripts/
    read-version.sh          # mod_version do gradle.properties + validação semver
    changelog-section.sh     # extrai "## [x.y.z]" e "## x.y.z" do CHANGELOG.md
    onboard-repo.sh          # gh api: environment, rulesets e cópia dos callers
  schemas/mod-pipeline.schema.json   # autocomplete/validação do config no editor
  templates/                         # o que vai para cada mod
    ci.yml  tag.yml  release.yml  dependabot.yml  mod-pipeline.json
  README.md
```

Versionamento do mc-ci:
- Tags semver e uma major móvel `v1`. Os mods chamam `@v1`.
- Breaking changes vão para `v2`.
- Durante o desenvolvimento, um repo canário aponta para `@main`.

### Config por mod: `.github/mod-pipeline.json`

É a única coisa que varia entre os repos. Substitui os hardcodes atuais (glob de jar, JDKs, tasks).

```json
{
  "$schema": "https://raw.githubusercontent.com/<org>/mc-ci/v1/schemas/mod-pipeline.schema.json",
  "displayName": "Copycat Replace",
  "java": [17, 21],
  "checks": ["buildAll", "verifyAll"],
  "curseforge": { "projectId": "1662789", "releaseType": "auto" },
  "targets": [
    { "id": "neoforge-1.21.1", "task": ":neoforge:build", "files": ["neoforge/build/libs/*.jar"],
      "loaders": ["neoforge"], "gameVersions": ["1.21.1"], "java": 21, "dependencies": [] },
    { "id": "forge-1.20.1", "task": ":forge1201:build", "files": ["forge1201/build/libs/*.jar"],
      "loaders": ["forge"], "gameVersions": ["1.20.1"], "java": 17, "dependencies": [] }
  ]
}
```

- **Mod single-loader:** um target, com `task: "build"` e `files: ["build/libs/*.jar"]`.
- **`files`:** o primeiro arquivo é o principal. Os demais, como `-sources`, vão como arquivos adicionais. Jars `-dev`, `-dev-shadow` e `-slim` são excluídos por padrão.
- **`releaseType: "auto"`:** `-alpha*` vira alpha, `-beta*`/`-rc*` vira beta, o resto vira release. Também aceita um valor fixo.

### Composite `setup-build`

1. `setup-java` com todos os JDKs de `java[]`.
2. Grava `~/.gradle/gradle.properties` com `org.gradle.java.installations.fromEnv=JAVA_HOME_17_X64,...` e `auto-download=false`. Isso substitui o `-Porg.gradle.java.installations.paths` manual do hotbar-locker.
3. `setup-gradle` com cache gravável só na default branch e validação do wrapper.
4. `chmod +x gradlew`, porque os repos vêm do Windows.

## Os 3 workflows reutilizáveis

### `mod-ci.yml` (PR)

- **Trigger no caller:** `pull_request` na default branch, mais `workflow_dispatch`.
- **Permissões e segredos:** `contents: read` e nenhum secret, então PRs de fork são seguros. Concurrency por PR com `cancel-in-progress`.
- **`config`:** roda o `read-config` e gera a matrix de targets.
- **`checks`:** roda uma vez com todos os JDKs `./gradlew <checks...> --console=plain --stacktrace`. Cobre JUnit, GameTests via `runGameTestServer`/`verifyAll` e as tasks `verify*`. Em caso de falha, sobe `**/build/reports/**` como artefato.
- **`build` (matrix por target, `fail-fast: false`):**
  - Roda `./gradlew <task>`.
  - Confere que o glob `files` casa com pelo menos 1 jar.
  - Sobe os jars como artefato `jars-<id>`, com retenção de 7 dias, para testar o PR in-game.
- **`release-preview`:**
  - Lê o `mod_version` do PR e informa no job summary se o merge vai gerar `vX.Y.Z` ou se não gera release.
  - Falha se a versão já existe como tag com conteúdo diferente, ou se não for semver.
  - Avisa, sem falhar, se o CHANGELOG não tiver a seção da versão.
- **`result`:** job agregador `if: always()`. É o único nome estável usado como required status check no ruleset. Os nomes dos jobs da matrix variam por repo.

### `mod-tag.yml` (merge/push na default branch)

- **Trigger no caller:** `push` em `main`, ou `master` nos 3 repos que ainda usam master.
- **Permissões:** `contents: read`. Concurrency por repo, sem cancelamento.
- Passos:
  1. `read-version.sh` lê o `mod_version`.
  2. Se a tag `v<ver>` já existe, termina com um notice. Merge sem bump não gera release.
  3. `create-github-app-token` com `vars.RELEASE_APP_ID` e `secrets.RELEASE_APP_PRIVATE_KEY`, com escopo só no repo atual e `contents: write`.
  4. Cria a tag **anotada** `v<ver>` no SHA do push, via API, usando o token da App. Por ser da App, o push de tag dispara o `release.yml`.

### `mod-release.yml` (push de tag `v*`)

- **Trigger no caller:** `push: tags: ['v*']`. Concurrency por tag, sem cancelamento.

Jobs:

1. **`prepare`**
   - Checkout na tag.
   - **Falha se a tag ≠ `v${mod_version}`.** Isso protege contra tag manual errada.
   - Calcula o releaseType e extrai a seção do CHANGELOG. Sem seção, usa um link para o compare entre tags.
   - Emite a matrix.
2. **`build`** (matrix)
   - Mesmo `setup-build`.
   - Roda `checks` (desligável por input `run-checks`, padrão true) e depois `<task>`.
   - Sobe `jars-<id>` com retenção de 90 dias e grava os SHA-256 no job summary.
3. **`publish`** (matrix, `needs: build`, **`environment: curseforge`**)
   - Fica pendente até a aprovação no environment.
   - Baixa o `jars-<id>` e roda o `mc-publish` só com `curseforge-id`/`curseforge-token`.
   - Entradas: `version: <ver>+<id>`, `name: "<displayName> <ver> (<Loader> <MC>)"`, `loaders`, `game-versions`, `java`, `dependencies`, `version-type`, `changelog` e `retry-attempts`.
   - O arquivo entra no CurseForge já como publicado. A única outra barreira é a moderação do próprio CurseForge.

Permissões: `contents: read` em todos os jobs. O `CURSEFORGE_TOKEN` é passado **explicitamente**, não via `secrets: inherit`, e só o job `publish` o referencia.

### Callers em cada mod (`templates/`)

Cada caller tem cerca de 10 linhas. Exemplo de release:

```yaml
name: Release
on: { push: { tags: ['v*'] } }
permissions: { contents: read }
jobs:
  release:
    uses: <org>/mc-ci/.github/workflows/mod-release.yml@v1
    secrets:
      CURSEFORGE_TOKEN: ${{ secrets.CURSEFORGE_TOKEN }}
```

`ci.yml` e `tag.yml` seguem o mesmo formato. O `tag.yml` passa `RELEASE_APP_PRIVATE_KEY`.

## Autenticação, aprovação e proteção (nível org)

| Item | Onde | Conteúdo |
|---|---|---|
| `CURSEFORGE_TOKEN` | secret de org, visível a repos selecionados | API token do CurseForge |
| GitHub App `mc-release-bot` | instalada nos repos de mods | permissão só `contents: write` |
| `RELEASE_APP_ID` / `RELEASE_APP_PRIVATE_KEY` | variável / secret de org | credenciais da App |
| Environment `curseforge` | em cada repo, criado por `onboard-repo.sh` | required reviewer = você; prevent self-review off; deployment policy só tags `v*` |
| Ruleset de branch (org) | default branch | PR obrigatório, status `CI / result` obrigatório, sem force-push |
| Ruleset de tag (org) | `refs/tags/v*` | bloqueia update/delete; criação só App + admin |

**Enquanto a org não existe:** funciona igual com secrets e variáveis de repo de mesmo nome. Na migração para a org, basta apagar os de repo.

## Pré-requisitos de onboarding a registrar no README (sem executar agora)

- **Jars locais não versionados quebram no runner.** São o caso de `sophisticated-backpack-is-addon` (`libs/scc-*.jar`), `minecolonies-butler`, `sable-horses` (`run/mods`), `hqspeaker-sable-compat` e `flight-safety-instruments`. Precisam ir para CurseMaven/Modrinth Maven ou ser commitados.
- **Versão hardcoded no `build.gradle`:** RoadWeaver e tectonic. São forks de terceiros e ficam fora.
- **IDs do CurseForge vêm do `mod-docs`:** copycat-replace 1662789, fly-by-instruments 1766429, hotbar-locker 1702281, sophisticated-backpack 1742266.
- **Comportamento muda em relação ao template atual:**
  - A tag deixa de vir de Conventional Commits e passa a vir do `mod_version`.
  - Deixa de existir GitHub Release; os jars ficam como artefato do run.
  - Os `auto-tag.yml`, `pr-checks.yml` e `release-on-tag.yml` antigos são removidos no onboarding.

## Verificação (quando for implementar)

1. `self-test.yml` verde no mc-ci: actionlint, zizmor sem findings high e testes dos scripts com CHANGELOG nos dois formatos.
2. Canário single-loader (simply-light-smart) e multi-loader (hotbar-locker ou copycat-replace) apontando para `@main`:
   - PR → `checks`, um build por target e `result` verdes; o summary mostra o preview da versão.
   - Merge sem bump → nenhuma tag.
   - Merge com bump → tag `vX.Y.Z` criada pela App → run de Release dispara sozinho.
   - O `publish` fica em "Waiting for review" → aprovar → os arquivos aparecem no CurseForge com loader e MC corretos. No primeiro teste, usar `releaseType: alpha`.
   - Tag manual com versão divergente do `gradle.properties` → `prepare` falha.
   - PR de fork → roda sem acesso a secrets.
3. Taguear o mc-ci como `v1.0.0`/`v1`, trocar os canários para `@v1` e só então fazer o onboarding dos demais.
