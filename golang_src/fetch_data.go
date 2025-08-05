package main

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"time"
	"log"
	"os"
	
)

const (
	BaseURL = "https://ballchasing.com/api"
)

// Client represents a Ballchasing API client
type Client struct {
	HTTPClient *http.Client
	APIKey     string
}

// NewClient creates a new Ballchasing API client
func NewClient(apiKey string) *Client {
	return &Client{
		HTTPClient: &http.Client{
			Timeout: time.Second * 30,
		},
		APIKey: apiKey,
	}
}

// Replay represents a replay from the API
type Replay struct {
	ID          string    `json:"id"`
	Title       string    `json:"title"`
	CreatedAt   time.Time `json:"created"`
	Status      string    `json:"status"`
	RocketLeagueID string `json:"rocket_league_id"`
	MatchGUID   string    `json:"match_guid"`
	Date        time.Time `json:"date"`
	MapCode     string    `json:"map_code"`
	MapName     string    `json:"map_name"`
	Playlist    struct {
		ID   int    `json:"id"`
		Name string `json:"name"`
	} `json:"playlist"`
	Duration int `json:"duration"`
	Overtime bool `json:"overtime"`
	Season   int  `json:"season"`
}

// ReplayList represents the response from the replays endpoint
type ReplayList struct {
	List []Replay `json:"list"`
	Count int     `json:"count"`
}

// Player represents a player in a replay
type Player struct {
	ID   struct {
		ID       string `json:"id"`
		Platform string `json:"platform"`
	} `json:"id"`
	Name  string `json:"name"`
	Team  int    `json:"team"`
	Score int    `json:"score"`
	Goals int    `json:"goals"`
	Saves int    `json:"saves"`
	Assists int  `json:"assists"`
	Stats struct {
		Core struct {
			Shots      int     `json:"shots"`
			ShotsAgainst int   `json:"shots_against"`
			Goals      int     `json:"goals"`
			GoalsAgainst int   `json:"goals_against"`
			Saves      int     `json:"saves"`
			Assists    int     `json:"assists"`
			Score      int     `json:"score"`
			MVPs       int     `json:"mvp"`
			ShootingPercentage float64 `json:"shooting_percentage"`
		} `json:"core"`
	} `json:"stats"`
}

// ReplayDetails represents detailed replay information
type ReplayDetails struct {
	ID       string   `json:"id"`
	Title    string   `json:"title"`
	Date     time.Time `json:"date"`
	Duration int      `json:"duration"`
	Blue     struct {
		Name    string   `json:"name"`
		Players []Player `json:"players"`
	} `json:"blue"`
	Orange struct {
		Name    string   `json:"name"`
		Players []Player `json:"players"`
	} `json:"orange"`
}

// makeRequest makes an HTTP request to the Ballchasing API
func (c *Client) makeRequest(endpoint string, params url.Values) ([]byte, error) {
	reqURL := fmt.Sprintf("%s%s", BaseURL, endpoint)
	
	if len(params) > 0 {
		reqURL += "?" + params.Encode()
	}

	req, err := http.NewRequest("GET", reqURL, nil)
	if err != nil {
		return nil, fmt.Errorf("creating request: %w", err)
	}

	// Add API key to headers
	if c.APIKey != "" {
		req.Header.Set("Authorization", c.APIKey)
	}

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("making request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("API returned status %d", resp.StatusCode)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("reading response: %w", err)
	}

	return body, nil
}

// GetReplays fetches a list of replays with optional filters
func (c *Client) GetReplays(params map[string]string) (*ReplayList, error) {
	urlParams := url.Values{}
	for k, v := range params {
		urlParams.Set(k, v)
	}

	data, err := c.makeRequest("/replays", urlParams)
	if err != nil {
		return nil, err
	}

	var replays ReplayList
	if err := json.Unmarshal(data, &replays); err != nil {
		return nil, fmt.Errorf("unmarshaling replays: %w", err)
	}

	return &replays, nil
}

// GetReplay fetches detailed information about a specific replay
func (c *Client) GetReplay(replayID string) (*ReplayDetails, error) {
	endpoint := fmt.Sprintf("/replays/%s", replayID)
	
	data, err := c.makeRequest(endpoint, nil)
	if err != nil {
		return nil, err
	}

	var replay ReplayDetails
	if err := json.Unmarshal(data, &replay); err != nil {
		return nil, fmt.Errorf("unmarshaling replay details: %w", err)
	}

	return &replay, nil
}

// GetReplaysByRank fetches replays filtered by rank
func (c *Client) GetReplaysByRank(minRank, maxRank string, count int) (*ReplayList, error) {
	params := map[string]string{
		"min-rank": minRank,
		"max-rank": maxRank,
		"count":    fmt.Sprintf("%d", count),
	}
	return c.GetReplays(params)
}

// GetReplaysByPlaylist fetches replays from a specific playlist
func (c *Client) GetReplaysByPlaylist(playlistID string, count int) (*ReplayList, error) {
	params := map[string]string{
		"playlist": playlistID,
		"count":    fmt.Sprintf("%d", count),
	}
	return c.GetReplays(params)
}

// SearchReplays searches for replays with a specific title
func (c *Client) SearchReplays(title string, count int) (*ReplayList, error) {
	params := map[string]string{
		"title": title,
		"count": fmt.Sprintf("%d", count),
	}
	return c.GetReplays(params)
}

// NewClientFromEnv creates a client using environment variables
func NewClientFromEnv() *Client {
	apiKey := os.Getenv("BALLCHASING_API_KEY")
	if apiKey == "" {
		log.Fatal("BALLCHASING_API_KEY environment variable is required")
	}
	return NewClient(apiKey)
}

func main() {
	// Create client from environment variable
	client := NewClientFromEnv()

	// Example 1: Get 10 recent replays
	fmt.Println("Fetching recent replays...")
	replays, err := client.GetReplays(map[string]string{
		"count": "10",
	})
	if err != nil {
		log.Fatalf("Error fetching replays: %v", err)
	}

	fmt.Printf("Found %d replays:\n", len(replays.List))
	for i, replay := range replays.List {
		fmt.Printf("%d. %s (ID: %s, Duration: %ds)\n", 
			i+1, replay.Title, replay.ID, replay.Duration)
	}

	// Example 2: Get replays for specific player
	fmt.Println("\nFetching replays for player 'riainoo'...")
	playerReplays, err := client.GetReplays(map[string]string{
		"player-name": "riainoo",
		"count":       "5",
	})
	if err != nil {
		log.Printf("Error fetching player replays: %v", err)
	} else {
		fmt.Printf("Found %d replays for riainoo:\n", len(playerReplays.List))
		for i, replay := range playerReplays.List {
			fmt.Printf("%d. %s (%s)\n", 
				i+1, replay.Title, replay.Date.Format("2006-01-02"))
		}
	}

	// Example 3: Get specific replay details (if group ID is provided)
	groupID := os.Getenv("BALLCHASING_GROUP_ID")
	if groupID != "" {
		fmt.Printf("\nFetching details for replay/group: %s\n", groupID)
		details, err := client.GetReplay(groupID)
		if err != nil {
			log.Printf("Error fetching replay details: %v", err)
		} else {
			fmt.Printf("Replay: %s\n", details.Title)
			fmt.Printf("Duration: %d seconds\n", details.Duration)
			fmt.Printf("Blue team players: %d\n", len(details.Blue.Players))
			fmt.Printf("Orange team players: %d\n", len(details.Orange.Players))

			// Print player stats
			fmt.Println("\nBlue team:")
			for _, player := range details.Blue.Players {
				fmt.Printf("  - %s: %d goals, %d saves, %d assists\n", 
					player.Name, player.Goals, player.Saves, player.Assists)
			}

			fmt.Println("\nOrange team:")
			for _, player := range details.Orange.Players {
				fmt.Printf("  - %s: %d goals, %d saves, %d assists\n", 
					player.Name, player.Goals, player.Saves, player.Assists)
			}
		}
	} else {
		fmt.Println("\nSet BALLCHASING_GROUP_ID environment variable to fetch specific replay details")
	}
}