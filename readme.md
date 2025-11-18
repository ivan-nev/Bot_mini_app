Монтирование папки для загрузки в облако

s3fs vikunja-files $HOME/vikunja_files -o passwd_file=$HOME/.passwd-s3fs   -o url=https://storage.yandexcloud.net -o use_path_request_style   -o allow_other   -o nonempty

s3fs bucket-ccfbdd $HOME/test -o passwd_file=$HOME/.passwd-s3fs-cloud   -o url=https://s3.cloud.ru -o use_path_request_style   -o allow_other   -o nonempty