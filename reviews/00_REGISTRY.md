<!-- review-coverage-registry: content=c90135b94bc249b08e845a2108071659e2eafbfe -->
# Реестр богословской рецензии тестов

Реестр охватывает все 13 книг из `manifest.json`: 1365
опубликованный вопрос и 0 вопросов в черновиках. Для каждого вопроса
существует стабильный ID и отдельное поле вердикта.

Наличие пакета не означает, что рецензия завершена. Пока заполненный вердикт
богословски грамотного человека не зафиксирован в репозитории, статус
человеческой рецензии остаётся «ожидается».

- Входной commit: `c90135b94bc249b08e845a2108071659e2eafbfe`
- Всего подготовлено к проверке: 1365 вопросов.

| Книга | Статус тестов | Вопросы | Пакет | Человеческая рецензия |
|---|---|---:|---|---|
| Афанасий Великий · «Слово о воплощении Бога-Слова» | опубликованы | 27 | [01_afanasij.md](early_fathers/01_afanasij.md) | ожидается |
| Макарий Великий · «Духовные беседы» | опубликованы | 150 | [02_makarij_001_025.md](early_fathers/02_makarij_001_025.md)<br>[03_makarij_026_050.md](early_fathers/03_makarij_026_050.md) | ожидается |
| Иоанн Златоуст · «Беседы о покаянии» | опубликованы | 27 | [04_zlatoust.md](early_fathers/04_zlatoust.md) | ожидается |
| Иоанн Златоуст · «О священстве» | опубликованы | 18 | [05_zlatoust_svjashhenstvo.md](early_fathers/05_zlatoust_svjashhenstvo.md) | ожидается |
| Иоанн Златоуст · «Восемь слов на Книгу Бытия» | опубликованы | 24 | [06_zlatoust_bytie.md](early_fathers/06_zlatoust_bytie.md) | ожидается |
| Кирилл Иерусалимский · «Огласительные и тайноводственные поучения» | опубликованы | 72 | [01_chapters_001_012.md](kirill_ierusalimskij/01_chapters_001_012.md)<br>[02_chapters_013_024.md](kirill_ierusalimskij/02_chapters_013_024.md) | ожидается |
| Василий Великий · «О Святом Духе» | опубликованы | 90 | [07_basil_spirit_001_015.md](early_fathers/07_basil_spirit_001_015.md)<br>[08_basil_spirit_016_030.md](early_fathers/08_basil_spirit_016_030.md) | ожидается |
| Авва Дорофей · «Душеполезные поучения» | опубликованы | 63 | [03_avva_dorofey.md](v1.3.1/03_avva_dorofey.md) | ожидается |
| Иоанн Лествичник · «Лествица» | опубликованы | 90 | [01_lestvitsa.md](v1.3.1/01_lestvitsa.md) | ожидается |
| Иоанн Дамаскин · «Точное изложение православной веры» | опубликованы | 300 | [01_chapters_001_025.md](ioann_damaskin/01_chapters_001_025.md)<br>[02_chapters_026_050.md](ioann_damaskin/02_chapters_026_050.md)<br>[03_chapters_051_075.md](ioann_damaskin/03_chapters_051_075.md)<br>[04_chapters_076_100.md](ioann_damaskin/04_chapters_076_100.md) | ожидается |
| Феофан Затворник · «Путь ко спасению» | опубликованы | 84 | [02_feofan.md](v1.3.1/02_feofan.md) | ожидается |
| Феофан Затворник · «Что есть духовная жизнь и как на неё настроиться?» | опубликованы | 240 | [01_letters_001_020.md](feofan_dukhovnaja_zhizn/01_letters_001_020.md)<br>[02_letters_021_040.md](feofan_dukhovnaja_zhizn/02_letters_021_040.md)<br>[03_letters_041_060.md](feofan_dukhovnaja_zhizn/03_letters_041_060.md)<br>[04_letters_061_080.md](feofan_dukhovnaja_zhizn/04_letters_061_080.md) | ожидается |
| Игнатий (Брянчанинов) · «Приношение современному монашеству» | опубликованы | 180 | [01_chapters_001_015.md](ignatij_prinoshenie/01_chapters_001_015.md)<br>[02_chapters_016_030.md](ignatij_prinoshenie/02_chapters_016_030.md)<br>[03_chapters_031_045.md](ignatij_prinoshenie/03_chapters_031_045.md)<br>[04_chapters_046_060.md](ignatij_prinoshenie/04_chapters_046_060.md) | ожидается |

## Контроль

```sh
python3 tools/audit_review_coverage.py
```

Аудитор требует, чтобы каждая книга манифеста присутствовала в реестре, число
вопросов совпадало с исходными JSON или полным комплектом черновиков, а пакет
содержал ровно по одному уникальному ID и полю вердикта на вопрос.
