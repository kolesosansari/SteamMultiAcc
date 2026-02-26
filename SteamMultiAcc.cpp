#pragma execution_character_set("utf-8")
#include "imgui.h"
#include "imgui_impl_win32.h"
#include "imgui_impl_dx11.h"
#include <d3d11.h>
#include <tchar.h>
#include <iostream>
#include <string>
#include <vector>
#include <fstream>
#include <windows.h>

// Указываем компилятору подключить библиотеку DirectX 11
#pragma comment(lib, "d3d11.lib")

using namespace std;

// --- НАША ЛОГИКА ИЗ ПРОШЛОГО ШАГА ---
struct Account {
    string username;
    string password;
};

void LoginSteam(string username, string password) {
    system("taskkill /f /im steam.exe >nul 2>&1");
    Sleep(2000);
    string steamPath = "C:\\Program Files (x86)\\Steam\\steam.exe";
    string params = "-login \"" + username + "\" \"" + password + "\"";
    ShellExecuteA(NULL, "open", steamPath.c_str(), params.c_str(), NULL, SW_SHOWNORMAL);
}

vector<Account> LoadAccounts() {
    vector<Account> accounts;
    ifstream file("accounts.txt");
    if (!file.is_open()) {
        ofstream newFile("accounts.txt");
        newFile << "Login1 Password1\nLogin2 Password2\n";
        newFile.close();
        return accounts;
    }
    string u, p;
    while (file >> u >> p) {
        accounts.push_back({ u, p });
    }
    file.close();
    return accounts;
}
// ------------------------------------

// --- БОЙЛЕРПЛЕЙТ DIRECTX 11 И СОЗДАНИЯ ОКНА ---
static ID3D11Device* g_pd3dDevice = nullptr;
static ID3D11DeviceContext* g_pd3dDeviceContext = nullptr;
static IDXGISwapChain* g_pSwapChain = nullptr;
static ID3D11RenderTargetView* g_mainRenderTargetView = nullptr;

void CreateRenderTarget() {
    ID3D11Texture2D* pBackBuffer;
    g_pSwapChain->GetBuffer(0, IID_PPV_ARGS(&pBackBuffer));
    g_pd3dDevice->CreateRenderTargetView(pBackBuffer, nullptr, &g_mainRenderTargetView);
    pBackBuffer->Release();
}

void CleanupRenderTarget() {
    if (g_mainRenderTargetView) { g_mainRenderTargetView->Release(); g_mainRenderTargetView = nullptr; }
}

bool CreateDeviceD3D(HWND hWnd) {
    DXGI_SWAP_CHAIN_DESC sd;
    ZeroMemory(&sd, sizeof(sd));
    sd.BufferCount = 2;
    sd.BufferDesc.Width = 0;
    sd.BufferDesc.Height = 0;
    sd.BufferDesc.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
    sd.BufferDesc.RefreshRate.Numerator = 60;
    sd.BufferDesc.RefreshRate.Denominator = 1;
    sd.Flags = DXGI_SWAP_CHAIN_FLAG_ALLOW_MODE_SWITCH;
    sd.BufferUsage = DXGI_USAGE_RENDER_TARGET_OUTPUT;
    sd.OutputWindow = hWnd;
    sd.SampleDesc.Count = 1;
    sd.SampleDesc.Quality = 0;
    sd.Windowed = TRUE;
    sd.SwapEffect = DXGI_SWAP_EFFECT_DISCARD;

    UINT createDeviceFlags = 0;
    D3D_FEATURE_LEVEL featureLevel;
    const D3D_FEATURE_LEVEL featureLevelArray[2] = { D3D_FEATURE_LEVEL_11_0, D3D_FEATURE_LEVEL_10_0, };
    HRESULT res = D3D11CreateDeviceAndSwapChain(nullptr, D3D_DRIVER_TYPE_HARDWARE, nullptr, createDeviceFlags, featureLevelArray, 2, D3D11_SDK_VERSION, &sd, &g_pSwapChain, &g_pd3dDevice, &featureLevel, &g_pd3dDeviceContext);
    if (res != S_OK) return false;
    CreateRenderTarget();
    return true;
}

void CleanupDeviceD3D() {
    CleanupRenderTarget();
    if (g_pSwapChain) { g_pSwapChain->Release(); g_pSwapChain = nullptr; }
    if (g_pd3dDeviceContext) { g_pd3dDeviceContext->Release(); g_pd3dDeviceContext = nullptr; }
    if (g_pd3dDevice) { g_pd3dDevice->Release(); g_pd3dDevice = nullptr; }
}

extern IMGUI_IMPL_API LRESULT ImGui_ImplWin32_WndProcHandler(HWND hWnd, UINT msg, WPARAM wParam, LPARAM lParam);
LRESULT WINAPI WndProc(HWND hWnd, UINT msg, WPARAM wParam, LPARAM lParam) {
    if (ImGui_ImplWin32_WndProcHandler(hWnd, msg, wParam, lParam)) return true;
    switch (msg) {
    case WM_SIZE:
        if (g_pd3dDevice != nullptr && wParam != SIZE_MINIMIZED) {
            CleanupRenderTarget();
            g_pSwapChain->ResizeBuffers(0, (UINT)LOWORD(lParam), (UINT)HIWORD(lParam), DXGI_FORMAT_UNKNOWN, 0);
            CreateRenderTarget();
        }
        return 0;
    case WM_SYSCOMMAND:
        if ((wParam & 0xfff0) == SC_KEYMENU) return 0; // Отключаем меню по ALT
        break;
    case WM_DESTROY:
        PostQuitMessage(0);
        return 0;
    }
    return DefWindowProc(hWnd, msg, wParam, lParam);
}
// ------------------------------------

int main() {
    // Загружаем наши аккаунты из файла
    vector<Account> accounts = LoadAccounts();

    // Создаем окно Windows
    WNDCLASSEXW wc = { sizeof(wc), CS_CLASSDC, WndProc, 0L, 0L, GetModuleHandle(nullptr), nullptr, nullptr, nullptr, nullptr, L"SteamMultiClass", nullptr };
    ::RegisterClassExW(&wc);
    HWND hwnd = ::CreateWindowW(wc.lpszClassName, L"Steam Multi-Acc by Boss", WS_OVERLAPPEDWINDOW, 100, 100, 400, 500, nullptr, nullptr, wc.hInstance, nullptr);

    // Инициализируем Direct3D
    if (!CreateDeviceD3D(hwnd)) {
        CleanupDeviceD3D();
        ::UnregisterClassW(wc.lpszClassName, wc.hInstance);
        return 1;
    }

    ::ShowWindow(hwnd, SW_SHOWDEFAULT);
    ::UpdateWindow(hwnd);

    // Инициализируем ImGui
    IMGUI_CHECKVERSION();
    ImGui::CreateContext();
    ImGuiIO& io = ImGui::GetIO(); (void)io;
    io.Fonts->AddFontFromFileTTF("VMVSegaGenesis-Regular.otf", 10.0f, NULL, io.Fonts->GetGlyphRangesCyrillic());
    ImGui::StyleColorsDark(); // Темная тема (стильно)

    ImGui_ImplWin32_Init(hwnd);
    ImGui_ImplDX11_Init(g_pd3dDevice, g_pd3dDeviceContext);

    bool done = false;
    while (!done) {
        MSG msg;
        while (::PeekMessage(&msg, nullptr, 0U, 0U, PM_REMOVE)) {
            ::TranslateMessage(&msg);
            ::DispatchMessage(&msg);
            if (msg.message == WM_QUIT) done = true;
        }
        if (done) break;

        // Начинаем новый кадр ImGui
        ImGui_ImplDX11_NewFrame();
        ImGui_ImplWin32_NewFrame();
        ImGui::NewFrame();

        // --- РИСУЕМ НАШ ИНТЕРФЕЙС ---
        // Делаем окно ImGui на весь размер нашего Windows-окна
        // --- РИСУЕМ НАШ ИНТЕРФЕЙС ---
        ImGui::SetNextWindowPos(ImVec2(0, 0));
        ImGui::SetNextWindowSize(io.DisplaySize);
        ImGui::Begin("Accounts", nullptr, ImGuiWindowFlags_NoTitleBar | ImGuiWindowFlags_NoResize | ImGuiWindowFlags_NoMove);

        // Получаем ширину окна для центрирования
        float windowWidth = ImGui::GetWindowSize().x;

        // 1. РАДУЖНЫЙ ЗАГОЛОВОК ПО ЦЕНТРУ
        const char* titleText = "=== STEAM MULTI-ACC BOOTER ===";
        float titleWidth = ImGui::CalcTextSize(titleText).x;
        ImGui::SetCursorPosX((windowWidth - titleWidth) * 0.5f); // Сдвигаем курсор на середину

        // Генерируем цвет: берем время работы проги и переводим его в оттенок
        float time = (float)ImGui::GetTime();
        float hue = fmodf(time * 0.3f, 1.0f); // 0.3f — это скорость переливания (можешь поменять)
        float r, g, b;
        ImGui::ColorConvertHSVtoRGB(hue, 1.0f, 1.0f, r, g, b); // Переводим в RGB

        ImGui::TextColored(ImVec4(r, g, b, 1.0f), titleText); // Рисуем цветной текст

        ImGui::Separator();

        // КНОПКА ЗАПУСКА ПИТОН-ПАРСЕРА
        if (ImGui::Button("ОБНОВИТЬ СТАТИСТИКУ ДОТЫ", ImVec2(-1, 40))) {
            // Используем "py", так как через него у тебя все заработало
            system("py DotaParser/parser.py");
        }
        ImGui::Separator();
        // ------------------------------------

        if (accounts.empty()) {
            ImGui::Text("Файл accounts.txt пуст или не найден!");
        }
        else {
            // 2. ЦЕНТРИРУЕМ НАДПИСЬ "ДОСТУПНЫЕ АККАУНТЫ"
            const char* availText = "Доступные аккаунты";
            float availWidth = ImGui::CalcTextSize(availText).x;
            ImGui::SetCursorPosX((windowWidth - availWidth) * 0.5f);
            ImGui::Text(availText);

            ImGui::Spacing();
            ImGui::Spacing(); // Добавил чуть больше отступа перед кнопками

            // Генерируем кнопки для каждого аккаунта
            for (size_t i = 0; i < accounts.size(); i++) {
                if (ImGui::Button(accounts[i].username.c_str(), ImVec2(-1, 40))) {
                    LoginSteam(accounts[i].username, accounts[i].password);
                }
                ImGui::Spacing();
            }
        }

        ImGui::End();
        // ------------------------------

        // Рендеринг
        ImGui::Render();
        const float clear_color_with_alpha[4] = { 0.1f, 0.1f, 0.1f, 1.0f }; // Цвет фона за окном ImGui
        g_pd3dDeviceContext->OMSetRenderTargets(1, &g_mainRenderTargetView, nullptr);
        g_pd3dDeviceContext->ClearRenderTargetView(g_mainRenderTargetView, clear_color_with_alpha);
        ImGui_ImplDX11_RenderDrawData(ImGui::GetDrawData());

        g_pSwapChain->Present(1, 0); // VSync включен
    }

    // Очистка при выходе
    ImGui_ImplDX11_Shutdown();
    ImGui_ImplWin32_Shutdown();
    ImGui::DestroyContext();

    CleanupDeviceD3D();
    ::DestroyWindow(hwnd);
    ::UnregisterClassW(wc.lpszClassName, wc.hInstance);

    return 0;
}