// 1. ХАК: Подменяем глобальный Protobuf на версию 5 для библиотеки dota2
const ProtoBuf = require('protobufjs');
global.ProtoBuf = ProtoBuf; 

const SteamUser = require('steam-user');
const Dota2 = require('dota2'); // Теперь это сработает!
const fs = require('fs');
const path = require('path');

const accountsPath = path.join(__dirname, '../accounts.txt');
const statsPath = path.join(__dirname, '../stats.json');

// Читаем акки (как просил, на русском и по делу)
let accounts = [];
if (fs.existsSync(accountsPath)) {
    const data = fs.readFileSync(accountsPath, 'utf8');
    accounts = data.split('\n')
        .map(l => l.trim().split(/\s+/))
        .filter(p => p.length >= 2)
        .map(p => ({ user: p[0], pass: p[1] }));
}

let results = [];

async function checkNext(index) {
    if (index >= accounts.length) {
        console.log('\n✅ Работа окончена, босс! Файл stats.json готов.');
        fs.writeFileSync(statsPath, JSON.stringify(results, null, 4));
        process.exit(0);
    }

    const acc = accounts[index];
    console.log(`[${index + 1}/${accounts.length}] Заходим на ${acc.user}...`);

    const client = new SteamUser();
    const dota = new Dota2.Dota2Client(client, true);

    let info = { username: acc.user, avatar: "", rank: 0, lp: false };

    client.logOn({ accountName: acc.user, password: acc.pass });

    client.on('loggedOn', () => {
        client.setPersona(SteamUser.EPersonaState.Online);
        client.getPersonas([client.steamID], (personas) => {
            const p = personas[client.steamID.getSteamID64()];
            if (p) info.avatar = p.avatar_url_full;
            client.gamesPlayed([570]);
        });
    });

    dota.on('ready', () => {
        dota.requestProfileCard(client.steamID.accountid, (err, card) => {
            if (card) {
                info.rank = card.rank_tier || 0;
                // В этой версии библиотеки LP чекается через наличие даты окончания штрафа
                if (card.low_priority_until_date && card.low_priority_until_date > Date.now()/1000) {
                    info.lp = true;
                }
            }
            console.log(`-> Получено: Ранг ${info.rank}, LP: ${info.lp}`);
            results.push(info);
            client.logOff();
        });
    });

    client.on('error', (err) => {
        console.log(`-> Ошибка на ${acc.user}: ${err.message}`);
        results.push(info);
        setTimeout(() => checkNext(index + 1), 2000);
    });

    client.on('disconnected', () => {
        setTimeout(() => checkNext(index + 1), 2000);
    });
}

if (accounts.length > 0) checkNext(0);