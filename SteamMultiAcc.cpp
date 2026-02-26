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
#include <algorithm>

#pragma comment(lib, "d3d11.lib")

using namespace std;

struct MySteamAccount {
    string username;
    string password;
    string rank_name = "Unknown"; // Добавили имя ранга
    int mmr = 0;
    int behavior = 10000;         // Добавили порядочность
    bool lp = false;
};

void LoginSteam(string u, string p) {
    system("taskkill /f /im steam.exe >nul 2>&1");
    Sleep(2000);
    string steamPath = "C:\\Program Files (x86)\\Steam\\steam.exe";
    string params = "-login \"" + u + "\" \"" + p + "\"";
    ShellExecuteA(NULL, "open", steamPath.c_str(), params.c_str(), NULL, SW_SHOWNORMAL);
}

vector<MySteamAccount> LoadAccounts() {
    vector<MySteamAccount> accs;
    ifstream file("accounts.txt");
    if (!file.is_open()) {
        ofstream newFile("accounts.txt");
        newFile << "Login1 Password1\n";
        newFile.close();
        return accs;
    }
    string user, pass;
    while (file >> user >> pass) {
        MySteamAccount acc;
        acc.username = user;
        acc.password = pass;
        acc.rank = 0;
        acc.lp = false;
        accs.push_back(acc);
    }
    file.close();
    return accs;
}

void LoadStats(vector<MySteamAccount>& accList) {
    ifstream file("stats.json");
    if (!file.is_open()) return;
    string line, currentAcc;
    while (getline(file, line)) {
        if (line.find("\"username\":") != std::string::npos) {
            size_t s = line.find(": \"") + 3;
            currentAcc = line.substr(s, line.find("\"", s) - s);
        }
        if (line.find("\"rank_name\":") != std::string::npos) { // Ищем название медали
            size_t s = line.find(": \"") + 3;
            string rn = line.substr(s, line.find("\"", s) - s);
            for (auto& a : accList) if (a.username == currentAcc) a.rank_name = rn;
        }
        if (line.find("\"behavior\":") != std::string::npos) { // Ищем порядочность
            size_t pos = line.find(":");
            int beh = stoi(line.substr(pos + 1));
            for (auto& a : accList) if (a.username == currentAcc) a.behavior = beh;
        }
        if (line.find("\"lp\":") != std::string::npos) {
            bool isLp = (line.find("true") != std::string::npos);
            for (auto& a : accList) if (a.username == currentAcc) a.lp = isLp;
        }
    }
}

// --- DirectX 11 Boilerplate ---
static ID3D11Device* g_pd3dDevice = nullptr;
static ID3D11DeviceContext* g_pd3dDeviceContext = nullptr;
static IDXGISwapChain* g_pSwapChain = nullptr;
static ID3D11RenderTargetView* g_mainRenderTargetView = nullptr;

void CreateRenderTarget() {
    ID3D11Texture2D* pBackBuffer = nullptr;
    HRESULT hr = g_pSwapChain->GetBuffer(0, IID_PPV_ARGS(&pBackBuffer));
    if (SUCCEEDED(hr) && pBackBuffer != nullptr) {
        g_pd3dDevice->CreateRenderTargetView(pBackBuffer, nullptr, &g_mainRenderTargetView);
        pBackBuffer->Release();
    }
}

void CleanupRenderTarget() { if (g_mainRenderTargetView) { g_mainRenderTargetView->Release(); g_mainRenderTargetView = nullptr; } }

bool CreateDeviceD3D(HWND hWnd) {
    DXGI_SWAP_CHAIN_DESC sd = {};
    sd.BufferCount = 2;
    sd.BufferDesc.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
    sd.BufferUsage = DXGI_USAGE_RENDER_TARGET_OUTPUT;
    sd.OutputWindow = hWnd;
    sd.SampleDesc.Count = 1;
    sd.Windowed = TRUE;
    sd.SwapEffect = DXGI_SWAP_EFFECT_DISCARD;
    D3D_FEATURE_LEVEL fl;
    if (FAILED(D3D11CreateDeviceAndSwapChain(nullptr, D3D_DRIVER_TYPE_HARDWARE, nullptr, 0, nullptr, 0, D3D11_SDK_VERSION, &sd, &g_pSwapChain, &g_pd3dDevice, &fl, &g_pd3dDeviceContext))) return false;
    CreateRenderTarget();
    return true;
}

void CleanupDeviceD3D() {
    CleanupRenderTarget();
    if (g_pSwapChain) g_pSwapChain->Release();
    if (g_pd3dDeviceContext) g_pd3dDeviceContext->Release();
    if (g_pd3dDevice) g_pd3dDevice->Release();
}

extern IMGUI_IMPL_API LRESULT ImGui_ImplWin32_WndProcHandler(HWND hWnd, UINT msg, WPARAM wParam, LPARAM lParam);
LRESULT WINAPI WndProc(HWND hWnd, UINT msg, WPARAM wParam, LPARAM lParam) {
    if (ImGui_ImplWin32_WndProcHandler(hWnd, msg, wParam, lParam)) return true;
    if (msg == WM_SIZE && g_pd3dDevice != nullptr && wParam != SIZE_MINIMIZED) {
        CleanupRenderTarget();
        g_pSwapChain->ResizeBuffers(0, (UINT)LOWORD(lParam), (UINT)HIWORD(lParam), DXGI_FORMAT_UNKNOWN, 0);
        CreateRenderTarget();
        return 0;
    }
    if (msg == WM_DESTROY) { PostQuitMessage(0); return 0; }
    return DefWindowProc(hWnd, msg, wParam, lParam);
}

int main() {
    // ВЕЗДЕ ИСПОЛЬЗУЕМ ИМЯ accounts
    vector<MySteamAccount> accounts = LoadAccounts();
    LoadStats(accounts);

    WNDCLASSEXW wc = { sizeof(wc), CS_CLASSDC, WndProc, 0L, 0L, GetModuleHandle(nullptr), nullptr, nullptr, nullptr, nullptr, L"SteamMultiClass", nullptr };
    RegisterClassExW(&wc);
    HWND hwnd = CreateWindowW(wc.lpszClassName, L"Steam Multi-Acc Boss", WS_OVERLAPPEDWINDOW, 100, 100, 450, 600, nullptr, nullptr, wc.hInstance, nullptr);

    if (!CreateDeviceD3D(hwnd)) return 1;

    ShowWindow(hwnd, SW_SHOWDEFAULT);
    IMGUI_CHECKVERSION();
    ImGui::CreateContext();
    ImGuiIO& io = ImGui::GetIO();
    io.Fonts->AddFontFromFileTTF("VMVSegaGenesis-Regular.otf", 16.0f, NULL, io.Fonts->GetGlyphRangesCyrillic());
    ImGui_ImplWin32_Init(hwnd);
    ImGui_ImplDX11_Init(g_pd3dDevice, g_pd3dDeviceContext);

    while (true) {
        MSG msg;
        while (PeekMessage(&msg, nullptr, 0U, 0U, PM_REMOVE)) {
            TranslateMessage(&msg);
            DispatchMessage(&msg);
            if (msg.message == WM_QUIT) goto cleanup;
        }

        ImGui_ImplDX11_NewFrame();
        ImGui_ImplWin32_NewFrame();
        ImGui::NewFrame();

        ImGui::SetNextWindowPos(ImVec2(0, 0));
        ImGui::SetNextWindowSize(io.DisplaySize);
        ImGui::Begin("MainPanel", nullptr, ImGuiWindowFlags_NoTitleBar | ImGuiWindowFlags_NoResize);

        float t = (float)ImGui::GetTime();
        float r, g, b;
        ImGui::ColorConvertHSVtoRGB(fmodf(t * 0.5f, 1.0f), 1.0f, 1.0f, r, g, b);
        ImGui::TextColored(ImVec4(r, g, b, 1.0f), "=== STEAM MULTI-ACC BOOTER ===");
        ImGui::Separator();

        if (ImGui::Button("ОБНОВИТЬ ДАННЫЕ ИЗ ДОТЫ", ImVec2(-1, 40))) {
            system("py DotaParser/parser.py");
            LoadStats(accounts);
        }
        ImGui::Separator();

        for (size_t i = 0; i < accounts.size(); i++) {
            string label = accounts[i].username + " | " + accounts[i].rank_name;
            label += " | Beh: " + to_string(accounts[i].behavior);
            if (accounts[i].lp) label += " [LOW PRIO!]";

            if (ImGui::Button(label.c_str(), ImVec2(-1, 45))) {
                LoginSteam(accounts[i].username, accounts[i].password);
            }
            ImGui::Spacing();
        }

        ImGui::End();
        ImGui::Render();
        g_pd3dDeviceContext->OMSetRenderTargets(1, &g_mainRenderTargetView, nullptr);
        float clear_col[4] = { 0.1f, 0.1f, 0.1f, 1.0f };
        g_pd3dDeviceContext->ClearRenderTargetView(g_mainRenderTargetView, clear_col);
        ImGui_ImplDX11_RenderDrawData(ImGui::GetDrawData());
        g_pSwapChain->Present(1, 0);
    }

cleanup:
    ImGui_ImplDX11_Shutdown();
    ImGui_ImplWin32_Shutdown();
    ImGui::DestroyContext();
    CleanupDeviceD3D();
    return 0;
}