# Dependencias del sitio.
#
# El mismo Jekyll que compila en local compila en GitHub Actions: así lo que ves
# en http://127.0.0.1:4100 es exactamente lo que se publica.
#
#   bundle install                       <- una vez
#   bundle exec jekyll serve --port 4100 <- previsualizar
source "https://rubygems.org"

gem "jekyll", "~> 4.4.1"

group :jekyll_plugins do
  gem "jekyll-feed",     "~> 0.17"
  gem "jekyll-sitemap",  "~> 1.4"
  gem "jekyll-seo-tag",  "~> 2.8"
end

# Necesario con Ruby >= 3.0 para `jekyll serve`
gem "webrick", "~> 1.8"

# Comprueba enlaces e imágenes rotas antes de publicar
gem "html-proofer", "~> 5.0", group: :test
